from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from apps.cattle.models import Cattle
from apps.locations.models import Location, LocationType


class AllocationService:
    """
    Service to validate moves and suggest paddocks based on capacity and rules.
    """

    MAX_AU_PER_HA = 1.5

    @classmethod
    def get_au(cls, animal: Cattle) -> float:
        """
        Calculates Animal Unit for a single animal.
        AU = Weight / 450. Default to 1.0 if no weight.
        """
        if getattr(animal, "current_weight", None):
            return float(animal.current_weight) / 450.0
        return 1.0

    @classmethod
    def validate_move(cls, paddock: Location, animals: List[Cattle]) -> Dict[str, Any]:
        """
        Validates if a batch of animals can be moved to a specific paddock.
        Returns: { 'valid': Bool, 'warnings': List[str], 'errors': List[str] }
        """
        warnings = []
        errors = []

        # 1. Occupancy Check
        # Helper to get active cattle in the paddock
        current_occupants = paddock.cattle.filter(status=Cattle.STATUS_AVAILABLE)
        if current_occupants.exists():
            count = current_occupants.count()
            # Conceptual Rule: Mating batches shouldn't mix unless explicitly allowed.
            errors.append(
                _("Paddock occupied by %(count)s animals.") % {"count": count}
            )

        # 2. Capacity Check (Stocking Rate)
        # Calculate Incoming AU
        incoming_au = sum(cls.get_au(animal) for animal in animals)

        # Calculate Existing AU
        # Optimization: We could use aggregation if AU was a DB field, but it involves logic.
        current_au = 0.0
        for occ in current_occupants:
            current_au += cls.get_au(occ)

        total_au = current_au + incoming_au

        if paddock.area_hectares and paddock.area_hectares > 0:
            projected_rate = total_au / float(paddock.area_hectares)

            if projected_rate > cls.MAX_AU_PER_HA:
                warnings.append(
                    _(
                        "Overstock Risk: Projected rate %(rate).2f AU/ha (Max: %(max).1f)."
                    )
                    % {"rate": projected_rate, "max": cls.MAX_AU_PER_HA}
                )
        else:
            errors.append(str(_("Paddock has no defined area (0 ha).")))

        return {
            "valid": len(errors) == 0,
            "warnings": warnings,
            "errors": errors,
        }

    @classmethod
    def suggest_paddocks(cls, required_au: float) -> List[Location]:
        """
        Finds empty PASTURE locations that fit the herd (simplified).
        """
        # Find empty pastures
        candidates = (
            Location.objects.filter(type=LocationType.PASTURE, is_active=True)
            .exclude(cattle__status=Cattle.STATUS_AVAILABLE)
            .order_by("area_hectares")
        )

        suggestions = []
        for loc in candidates:
            # Basic capacity check
            if loc.area_hectares > 0:
                capacity = float(loc.area_hectares) * 1.5  # MAX_AU
                if capacity >= required_au:
                    suggestions.append(loc)

        return suggestions
