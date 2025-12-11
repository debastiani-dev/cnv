from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.base.models.mixins import PerformedByMixin
from apps.locations.models.location import Location


class MovementReason(models.TextChoices):
    ROTATION = "ROTATION", _("Rotation")
    WEANING = "WEANING", _("Weaning")
    MEDICAL = "MEDICAL", _("Medical Treatment")
    SALE = "SALE", _("Sale")
    WEIGHT_CHECK = "WEIGHT_CHECK", _("Weight Check")
    OTHER = "OTHER", _("Other")


class Movement(PerformedByMixin, BaseModel):
    """
    Tracks the history of moving batches of animals.
    """

    date = models.DateTimeField(_("Date"), default=timezone.now)
    origin = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements_out",
        verbose_name=_("Origin"),
        help_text=_("Source location. Null if purchase/entry."),
    )
    destination = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="movements_in",
        verbose_name=_("Destination"),
    )
    reason = models.CharField(
        _("Reason"),
        max_length=20,
        choices=MovementReason.choices,
        default=MovementReason.ROTATION,
    )
    animals = models.ManyToManyField(
        "cattle.Cattle",
        related_name="movements",
        verbose_name=_("Animals"),
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Movement")
        verbose_name_plural = _("Movements")
        ordering = ["-date"]

    def __str__(self):
        origin_name = self.origin.name if self.origin else "External"
        return f"{self.date.date()} - {self.get_reason_display()} ({origin_name} -> {self.destination.name})"
