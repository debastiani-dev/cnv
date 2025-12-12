from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import BaseModel
from apps.locations.models.location import Location
from apps.nutrition.models.diet import Diet


class FeedingEvent(BaseModel):
    date = models.DateField(_("Date"))
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="feeding_events",
        verbose_name=_("Location"),
    )
    diet = models.ForeignKey(
        Diet,
        on_delete=models.PROTECT,
        related_name="feeding_events",
        verbose_name=_("Diet"),
    )
    amount_kg = models.DecimalField(_("Amount (kg)"), max_digits=10, decimal_places=2)
    cost_total = models.DecimalField(
        _("Total Cost ($)"),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Calculated cost at time of feeding"),
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feeding_events",
        verbose_name=_("Performed By"),
    )

    class Meta:
        verbose_name = _("Feeding Event")
        verbose_name_plural = _("Feeding Events")
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} - {self.location} - {self.diet}"
