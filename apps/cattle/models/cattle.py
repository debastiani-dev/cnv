from datetime import date

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel


class Cattle(BaseModel):
    # Breed choices
    BREED_ANGUS = "angus"
    BREED_BRAHMAN = "brahman"
    BREED_HEREFORD = "hereford"
    BREED_HOLSTEIN = "holstein"
    BREED_JERSEY = "jersey"
    BREED_NELORE = "nelore"
    BREED_SIMMENTAL = "simmental"
    BREED_WAGYU = "wagyu"
    BREED_OTHER = "other"

    BREED_CHOICES = [
        (BREED_ANGUS, _("Angus")),
        (BREED_BRAHMAN, _("Brahman")),
        (BREED_HEREFORD, _("Hereford")),
        (BREED_HOLSTEIN, _("Holstein")),
        (BREED_JERSEY, _("Jersey")),
        (BREED_NELORE, _("Nelore")),
        (BREED_SIMMENTAL, _("Simmental")),
        (BREED_WAGYU, _("Wagyu")),
        (BREED_OTHER, _("Other")),
    ]

    # Status choices
    STATUS_AVAILABLE = "available"
    STATUS_SOLD = "sold"
    STATUS_DEAD = "dead"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, _("Available")),
        (STATUS_SOLD, _("Sold")),
        (STATUS_DEAD, _("Dead")),
    ]

    tag = models.CharField(_("Tag"), max_length=50, help_text=_("Ear tag or ID"))
    name = models.CharField(
        _("Name"),
        max_length=100,
        blank=True,
        help_text=_("Name/Nickname of the animal"),
    )
    breed = models.CharField(
        _("Breed"),
        max_length=20,
        choices=BREED_CHOICES,
        default=BREED_OTHER,
        blank=True,
    )
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

    @property
    def age(self):
        """
        Calculates the age of the cattle based on birth_date.
        Returns a string like "2y 5m" or "-" if birth_date is not set.
        """
        if not self.birth_date:
            return "-"

        today = date.today()
        # Calculate difference in months
        diff_years = today.year - self.birth_date.year
        diff_months = today.month - self.birth_date.month

        # Adjust for negative months (e.g. not yet birthday this year)
        if diff_months < 0:
            diff_years -= 1
            diff_months += 12

        if diff_years > 0:
            return f"{diff_years}y {diff_months}m"
        return f"{diff_months}m"

    def __str__(self):
        return f"{self.tag} ({self.get_status_display()})"
