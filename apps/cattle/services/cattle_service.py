from typing import Optional

from django.db.models import Count, Q, QuerySet

from apps.cattle.models import Cattle


class CattleService:
    @staticmethod
    def get_cattle_stats() -> dict:
        """
        Returns statistics about cattle.
        """
        total_cattle = Cattle.objects.filter(status=Cattle.STATUS_AVAILABLE).count()
        status_counts = Cattle.objects.values("status").annotate(count=Count("status"))

        # Convert QuerySet to a more usable dict
        stats = {item["status"]: item["count"] for item in status_counts}

        # Calculate breed breakdown
        # Calculate breed breakdown for active herd only
        active_cattle = Cattle.objects.filter(status=Cattle.STATUS_AVAILABLE)
        breed_counts = active_cattle.values("breed").annotate(count=Count("breed"))
        breed_dict = dict(Cattle.BREED_CHOICES)

        breed_stats = {}
        for item in breed_counts:
            code = item["breed"] or Cattle.BREED_OTHER
            label = breed_dict.get(
                code, code
            ).title()  # Fallback to code if not found, title cased
            breed_stats[label] = item["count"]

        return {
            "total": total_cattle,
            "status_breakdown": stats,
            "breed_breakdown": breed_stats,
            "available": stats.get(Cattle.STATUS_AVAILABLE, 0),
            "sold": stats.get(Cattle.STATUS_SOLD, 0),
            "dead": stats.get(Cattle.STATUS_DEAD, 0),
        }

    @staticmethod
    def get_productivity_stats() -> dict:
        """
        Returns pregnancy and mortality rates.
        """
        # 1. Pregnancy Rate
        # Formula: Pregnant / (Pregnant + Open)
        # We only care about cows that are biologically capable and having status tracked
        eligible_cows = Cattle.objects.filter(
            sex=Cattle.SEX_FEMALE,
            reproduction_status__in=[
                Cattle.REP_STATUS_PREGNANT,
                Cattle.REP_STATUS_OPEN,
                Cattle.REP_STATUS_BRED,
            ],
            status=Cattle.STATUS_AVAILABLE,
        ).count()

        pregnant_cows = Cattle.objects.filter(
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
        ).count()

        pregnancy_rate = 0.0
        if eligible_cows > 0:
            pregnancy_rate = round((pregnant_cows / eligible_cows) * 100, 1)

        # 2. Mortality Rate (All Time / Active Year - Simplification: All Time based on current DB state)
        # Using simple formula: Dead / (Alive + Dead)
        total_ever = Cattle.objects.count()
        dead_count = Cattle.objects.filter(status=Cattle.STATUS_DEAD).count()

        mortality_rate = 0.0
        if total_ever > 0:
            mortality_rate = round((dead_count / total_ever) * 100, 1)

        return {
            "pregnancy_rate": pregnancy_rate,
            "mortality_rate": mortality_rate,
            "pregnant_count": pregnant_cows,
            "dead_count": dead_count,
        }

    @staticmethod
    def get_all_cattle(
        search_query: Optional[str] = None,
        breed: Optional[str] = None,
        status: Optional[str] = None,
        location_id: Optional[str] = None,
    ) -> QuerySet[Cattle]:
        """
        Returns all cattle records optimized for display.
        Includes filter params for backward compatibility,
        but typically used as a base queryset for FilterSets.
        """
        queryset = (
            Cattle.objects.select_related("location", "sire", "dam")
            .all()
            .order_by("tag")
        )

        if search_query:
            queryset = queryset.filter(
                Q(tag__icontains=search_query) | Q(name__icontains=search_query)
            )

        if breed:
            queryset = queryset.filter(breed=breed)

        if status:
            queryset = queryset.filter(status=status)

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        return queryset

    @staticmethod
    def create_cattle(data: dict) -> Cattle:
        """Creates a new cattle record from valid data."""
        return Cattle.objects.create(**data)

    @staticmethod
    def update_cattle(cattle: Cattle, data: dict) -> Cattle:
        """Updates an existing cattle record."""
        for key, value in data.items():
            setattr(cattle, key, value)
        cattle.save()
        return cattle

    @staticmethod
    def get_deleted_cattle() -> QuerySet[Cattle]:
        """Returns all soft-deleted cattle records."""
        return Cattle.all_objects.filter(is_deleted=True).order_by("-modified_at")

    @staticmethod
    def restore_cattle(pk: int) -> Cattle:
        """
        Restores a soft-deleted cattle record.
        Raises ValueError if the tag is already in use by an active record.
        """
        cattle = Cattle.all_objects.get(pk=pk)

        # Check for conflict
        if Cattle.objects.filter(tag=cattle.tag).exists():
            raise ValueError(
                f"Cannot restore: Tag '{cattle.tag}' is already in use "
                f"by an active record."
            )

        cattle.restore()
        return cattle

    @staticmethod
    def hard_delete_cattle(pk: int) -> None:
        """Permanently deletes a cattle record from the database."""
        cattle = Cattle.all_objects.get(pk=pk)
        cattle.delete(destroy=True)

    @staticmethod
    def delete_cattle(cattle: Cattle) -> None:
        """Soft-deletes a cattle record."""
        cattle.delete()
