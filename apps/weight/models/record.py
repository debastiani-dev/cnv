from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.cattle.models.cattle import Cattle
from apps.weight.models.session import WeighingSession


class WeightRecord(BaseModel):
    """
    Represents the specific weight measurement for one animal within a session.
    """

    session = models.ForeignKey(
        WeighingSession,
        on_delete=models.CASCADE,
        related_name="records",
        verbose_name=_("Session"),
    )
    animal = models.ForeignKey(
        Cattle,
        on_delete=models.CASCADE,
        related_name="weight_records",
        verbose_name=_("Animal"),
    )

    weight_kg = models.DecimalField(_("Weight (kg)"), max_digits=8, decimal_places=2)

    # Performance Metrics (Persisted)
    adg = models.DecimalField(
        _("Average Daily Gain (kg/day)"),
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text=_("Gain per day since last weighing"),
    )
    days_since_prev_weight = models.PositiveIntegerField(
        _("Days since last weight"), null=True, blank=True
    )

    class Meta:
        verbose_name = _("Weight Record")
        verbose_name_plural = _("Weight Records")
        ordering = ["animal__tag"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "animal"],
                name="unique_animal_per_session",
                condition=models.Q(is_deleted=False),
            )
        ]

    def __str__(self):
        return f"{self.animal} - {self.weight_kg}kg"
