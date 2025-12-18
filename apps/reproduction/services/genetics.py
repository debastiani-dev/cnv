from typing import Set

from django.utils.translation import gettext_lazy as _

from apps.cattle.models import Cattle


class InbreedingService:
    """
    Service to calculate inbreeding coefficients and assess mating risks.
    """

    RISK_SAFE = "SAFE"
    RISK_WARNING = "WARNING"
    RISK_HIGH = "HIGH"
    RISK_CRITICAL = "CRITICAL"

    @classmethod
    def get_ancestors(cls, animal: Cattle, generations: int = 3) -> Set:
        """
        Recursively fetches ancestors' PKs up to a certain depth.
        Returns a set of ancestor PKs.
        """
        ancestors = set()
        if generations <= 0:
            return ancestors

        parents = []
        sire_id = getattr(animal, "sire_id", None)
        if sire_id:
            ancestors.add(sire_id)
            parents.append(animal.sire)

        dam_id = getattr(animal, "dam_id", None)
        if dam_id:
            ancestors.add(dam_id)
            parents.append(animal.dam)

        for parent in parents:
            ancestors.update(cls.get_ancestors(parent, generations - 1))

        return ancestors

    @classmethod
    def calculate_coefficient(cls, sire: Cattle, dam: Cattle) -> tuple[float, str, str]:
        """
        Calculates the inbreeding risk between a Sire and a Dam.
        Returns (coefficient, risk_level, reason).
        """
        # Critical Check: Direct Lineage (Parent/Child)
        dam_ancestors = cls.get_ancestors(dam, generations=3)
        if sire.pk in dam_ancestors:
            return (
                0.25,
                cls.RISK_CRITICAL,
                str(_("Sire is a direct ancestor of the Dam.")),
            )

        # Check reverse (Dam is ancestor of Sire?)
        sire_ancestors = cls.get_ancestors(sire, generations=3)
        if dam.pk in sire_ancestors:
            return (
                0.25,
                cls.RISK_CRITICAL,
                str(_("Dam is a direct ancestor of the Sire.")),
            )

        # High Risk: Half-Siblings (Share a parent)
        # We need immediate parents
        sire_parents = {getattr(sire, "sire_id"), getattr(sire, "dam_id")} - {None}
        dam_parents = {getattr(dam, "sire_id"), getattr(dam, "dam_id")} - {None}
        common_parents = sire_parents.intersection(dam_parents)

        if common_parents:
            return (
                0.125,
                cls.RISK_HIGH,
                str(_("Animals share a parent (Half-Siblings).")),
            )

        # Warning: Common Ancestors deeper down
        common_ancestors = sire_ancestors.intersection(dam_ancestors)
        if common_ancestors:
            return (
                0.0625,
                cls.RISK_WARNING,
                str(_("Common ancestors detected in last 3 generations.")),
            )

        return 0.0, cls.RISK_SAFE, str(_("No close common ancestors detected."))
