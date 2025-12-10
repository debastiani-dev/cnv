from django.db import models
from django.db.models.functions import Now
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.base.models.mixins import PerformedByMixin


class WeighingSessionType(models.TextChoices):
    ROUTINE = "ROUTINE", _("Routine")
    SALE = "SALE", _("Sale")
    PURCHASE = "PURCHASE", _("Purchase")
    WEANING = "WEANING", _("Weaning")
    BIRTH = "BIRTH", _("Birth")


class WeighingSession(PerformedByMixin, BaseModel):
    """
    Represents the event of weighing a specific group of animals on a specific day.
    Acts as a Header for WeightRecord details.
    """

    date = models.DateField(_("Date"), default=Now)
    name = models.CharField(_("Session Name"), max_length=150)
    notes = models.TextField(_("Notes"), blank=True)
    session_type = models.CharField(
        _("Type"),
        max_length=20,
        choices=WeighingSessionType.choices,
        default=WeighingSessionType.ROUTINE,
    )

    class Meta:
        verbose_name = _("Weighing Session")
        verbose_name_plural = _("Weighing Sessions")
        ordering = ["-date", "-created_at"]

    # Ignore records for strict deletion check (they are composition pieces, cascade deleted)
    strict_deletion_ignore_fields = ["records"]

    def __str__(self):
        return f"{self.date} - {self.name} ({self.get_session_type_display()})"
