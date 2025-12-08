from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel


class Cattle(BaseModel):
    tag = models.CharField(_("Tag"), max_length=50, help_text=_("Ear tag or ID"))
    name = models.CharField(
        _("Name"),
        max_length=100,
        blank=True,
        help_text=_("Name/Nickname of the animal"),
    )
    breed = models.CharField(_("Breed"), max_length=100, blank=True)
    birth_date = models.DateField(_("Birth Date"), blank=True, null=True)
    weight_kg = models.DecimalField(
        _("Weight (kg)"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    image = models.ImageField(
        _("Profile Image"),
        upload_to="cattle_images/",
        blank=True,
        null=True,
    )

    # Status choices
    STATUS_AVAILABLE = "available"
    STATUS_SOLD = "sold"
    STATUS_DEAD = "dead"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, _("Available")),
        (STATUS_SOLD, _("Sold")),
        (STATUS_DEAD, _("Dead")),
    ]
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Cattle")
        verbose_name_plural = _("Cattle")
        constraints = [
            models.UniqueConstraint(
                fields=["tag"],
                condition=models.Q(is_deleted=False),
                name="unique_active_cattle_tag",
            )
        ]

    def __str__(self):
        return f"{self.tag} ({self.get_status_display()})"
