from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel

if TYPE_CHECKING:
    from apps.cattle.models import Cattle


class LocationType(models.TextChoices):
    PASTURE = "PASTURE", _("Pasture")
    FEEDLOT = "FEEDLOT", _("Feedlot")
    CORRAL = "CORRAL", _("Corral")
    HOSPITAL = "HOSPITAL", _("Hospital")
    MATERNITY = "MATERNITY", _("Maternity")


class LocationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    RESTING = "RESTING", _("Resting")
    MAINTENANCE = "MAINTENANCE", _("Maintenance")


class Location(BaseModel):
    """
    Represents any physical space where animals can be kept.
    """

    name = models.CharField(_("Name"), max_length=100)
    type = models.CharField(
        _("Type"),
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.PASTURE,
    )
    area_hectares = models.DecimalField(
        _("Area (ha)"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Size of the area in hectares"),
    )
    capacity_head = models.PositiveIntegerField(
        _("Capacity (Head)"),
        help_text=_("Maximum recommended animals"),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_("If unchecked, the location is retired or fenced off."),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=LocationStatus.choices,
        default=LocationStatus.ACTIVE,
    )

    if TYPE_CHECKING:
        cattle: models.Manager["Cattle"]

    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")
        ordering = ["name"]

    def __str__(self):
        return self.name
