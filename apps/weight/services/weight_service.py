from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.db.models import Avg, QuerySet
from django.utils import timezone

from apps.cattle.models import Cattle
from apps.weight.models import WeighingSession, WeightRecord


class WeightService:
    @staticmethod
    @transaction.atomic
    def record_weight(
        session: WeighingSession, animal: Cattle, weight_kg: Decimal
    ) -> WeightRecord:
        """
        Records a weight for an animal, calculating ADG based on previous history.
        Updates the animal's current_weight and last_weighing_date.

        Args:
            session: The WeighingSession instance.
            animal: The Cattle instance.
            weight_kg: The new weight value.

        Returns:
            The created WeightRecord.
        """
        # 1. Fetch Previous Record
        # Find the most recent record strictly before this session's date
        previous_record = (
            WeightRecord.objects.filter(animal=animal, session__date__lt=session.date)
            .select_related("session")
            .order_by("-session__date")
            .first()
        )

        # 2. Calculate ADG
        adg: Optional[Decimal] = None
        days_diff: Optional[int] = None

        if previous_record:
            days_diff = (session.date - previous_record.session.date).days
            if days_diff > 0:
                weight_diff = weight_kg - previous_record.weight_kg
                # Calculate ADG: Kg gained / Days elapsed
                # Result is Kg/Day
                adg = weight_diff / Decimal(days_diff)

        # 3. Save Record
        # Update or create to allow re-weighing in same session (correction)
        record, _ = WeightRecord.objects.update_or_create(
            session=session,
            animal=animal,
            defaults={
                "weight_kg": weight_kg,
                "adg": adg,
                "days_since_prev_weight": days_diff,
            },
        )

        # 4. Update Cattle Inventory
        # We only update the inventory if this is the *latest* weighing.
        # This allows inserting historical records without messing up current state.
        if not animal.last_weighing_date or session.date >= animal.last_weighing_date:
            animal.current_weight = weight_kg
            animal.last_weighing_date = session.date
            animal.save(update_fields=["current_weight", "last_weighing_date"])

        return record

    @staticmethod
    def get_animal_weight_history(animal: Cattle) -> QuerySet[WeightRecord]:
        """
        Returns the weight history for a specific animal, ordered by date.
        """
        return (
            WeightRecord.objects.filter(animal=animal)
            .select_related("session")
            .order_by("session__date")
        )

    @staticmethod
    def get_herd_adg_stats(days: int = 90) -> dict:
        """
        Calculates the average ADG for the herd based on weighings in the last 'days'.
        """
        cutoff_date = timezone.now().date() - timedelta(days=days)

        # Average ADG of all records created in the last X days
        # where ADG is not null
        avg_adg = WeightRecord.objects.filter(
            session__date__gte=cutoff_date, adg__isnull=False
        ).aggregate(Avg("adg"))["adg__avg"]

        return {
            "avg_adg": round(avg_adg, 3) if avg_adg else 0.0,
            "days_period": days,
        }
