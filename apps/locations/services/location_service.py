from decimal import Decimal

from django.db import models
from django.db.models import Sum

from apps.locations.models import Location, LocationStatus


class LocationService:
    @staticmethod
    def calculate_stocking_rate(location: Location) -> dict:
        """
        Calculates KPIs for a location:
        - Total Weight (kg)
        - Stocking Rate (kg/ha)
        - Animal Units per Hectare (AU/ha) where 1 AU = 450kg

        Returns:
            dict: {
                "total_weight": Decimal,
                "kg_per_ha": Decimal,
                "au_per_ha": Decimal,
                "occupancy_rate": float (percentage of capacity_head)
            }
        """
        if not location.area_hectares or location.area_hectares <= 0:
            return {
                "total_weight": Decimal(0),
                "kg_per_ha": Decimal(0),
                "au_per_ha": Decimal(0),
                "occupancy_rate": 0.0,
            }

        cattle_in_location = location.cattle.filter(is_deleted=False)

        # Calculate Total Weight using current_weight cache
        # If current_weight is null, maybe fallback to weight_kg or 0?
        # Using 0 for integrity if unknown.
        aggregated = cattle_in_location.aggregate(total_weight=Sum("current_weight"))
        total_weight = aggregated["total_weight"] or Decimal(0)

        kg_per_ha = total_weight / Decimal(str(location.area_hectares))

        # 1 AU = 450kg
        au_per_ha = kg_per_ha / Decimal(450)

        head_count = cattle_in_location.count()
        occupancy = 0.0
        if location.capacity_head and location.capacity_head > 0:
            occupancy = (head_count / location.capacity_head) * 100

        return {
            "total_weight": round(total_weight, 2),
            "kg_per_ha": round(kg_per_ha, 2),
            "au_per_ha": round(au_per_ha, 2),
            "occupancy_rate": round(occupancy, 1),
            "head_count": head_count,
        }

    @staticmethod
    def get_dashboard_stats():
        """
        Returns stats for dashboard:
        - resting_violations: QuerySet of locations that are RESTING but have > 0 cattle.
        - top_occupancy: List of dicts for top 5 locations by occupancy (if capacity > 0).
        """
        # Resting violations
        resting_violations = (
            Location.objects.filter(status=LocationStatus.RESTING)
            .annotate(
                current_head_count=models.Count(
                    "cattle", filter=models.Q(cattle__is_deleted=False)
                )
            )
            .filter(current_head_count__gt=0)
        )

        # Top Occupancy
        # This is harder to do purely in ORM if capacity varies and we want %,
        # but we can do a rough fetch or just python sort for small number of locations.
        # For scalability, simple list.
        locations = Location.objects.filter(
            is_active=True, capacity_head__gt=0
        ).prefetch_related("cattle")
        occupancy_list = []
        for loc in locations:
            stats = LocationService.calculate_stocking_rate(loc)
            if stats["head_count"] > 0:
                occupancy_list.append(
                    {
                        "name": loc.name,
                        "occupancy_rate": stats["occupancy_rate"],
                        "head_count": stats["head_count"],
                        "capacity": loc.capacity_head,
                    }
                )

        # Sort by occupancy descending
        occupancy_list.sort(key=lambda x: x["occupancy_rate"], reverse=True)

        return {
            "resting_violations": resting_violations,
            "top_occupancy": occupancy_list[:5],
        }

    @staticmethod
    def get_deleted_locations():
        return Location.all_objects.filter(is_deleted=True).order_by("-modified_at")

    @staticmethod
    def restore_location(pk):
        location = Location.all_objects.get(pk=pk)
        location.restore()
        return location

    @staticmethod
    def hard_delete_location(pk):
        location = Location.all_objects.get(pk=pk)
        location.delete(destroy=True)
