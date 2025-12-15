from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import BaseModel

from .health import Medication


class HealthProtocol(BaseModel):
    """
    Defines a standard sanitary protocol (recipe) that contains multiple
    medications or procedures to be applied together.
    """

    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Active"), default=True)

    # Allow partial deletion (items are part of the protocol)
    strict_deletion_ignore_fields = ["items"]

    class Meta:
        verbose_name = _("Health Protocol")
        verbose_name_plural = _("Health Protocols")
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProtocolItem(BaseModel):
    """
    A specific item (medication/procedure) within a HealthProtocol.
    """

    protocol = models.ForeignKey(
        HealthProtocol,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Protocol"),
    )
    medication = models.ForeignKey(
        Medication, on_delete=models.RESTRICT, verbose_name=_("Medication")
    )
    default_dosage = models.CharField(
        _("Default Dosage"), max_length=50, help_text=_("E.g., 5ml, 1 dose, 10mg/kg")
    )
    notes = models.CharField(
        _("Notes"),
        max_length=255,
        blank=True,
        help_text=_("E.g., Subcutaneous, Left side of neck"),
    )

    class Meta:
        verbose_name = _("Protocol Item")
        verbose_name_plural = _("Protocol Items")
        ordering = ["protocol", "medication__name"]

    def __str__(self):
        return f"{self.medication.name} ({self.default_dosage})"
