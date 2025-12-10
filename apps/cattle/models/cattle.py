from datetime import date

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.purchases.models.purchase import PurchaseItem
from apps.sales.models.sale import SaleItem


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

    # Reproduction Status choices
    REP_STATUS_OPEN = "OPEN"
    REP_STATUS_BRED = "BRED"
    REP_STATUS_PREGNANT = "PREGNANT"
    REP_STATUS_LACTATING = "LACTATING"

    REP_STATUS_CHOICES = [
        (REP_STATUS_OPEN, _("Open")),
        (REP_STATUS_BRED, _("Bred")),
        (REP_STATUS_PREGNANT, _("Pregnant")),
        (REP_STATUS_LACTATING, _("Lactating")),
    ]

    # Sex choices
    SEX_MALE = "male"
    SEX_FEMALE = "female"
    SEX_CHOICES = [
        (SEX_MALE, _("Male")),
        (SEX_FEMALE, _("Female")),
    ]

    tag = models.CharField(_("Tag"), max_length=50, help_text=_("Ear tag or ID"))
    name = models.CharField(
        _("Name"),
        max_length=100,
        blank=True,
        help_text=_("Name/Nickname of the animal"),
    )
    electronic_id = models.CharField(
        _("Electronic ID"),
        max_length=100,
        blank=True,
        help_text=_("RFID or EID tag number"),
    )
    sex = models.CharField(
        _("Sex"),
        max_length=10,
        choices=SEX_CHOICES,
        default=SEX_FEMALE,
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

    reproduction_status = models.CharField(
        _("Reproduction Status"),
        max_length=20,
        choices=REP_STATUS_CHOICES,
        default=REP_STATUS_OPEN,
        blank=True,
        help_text=_("Biological status of the female."),
    )

    # Parentage (Hybrid Approach)
    sire = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offspring_sire",
        verbose_name=_("Sire (Internal)"),
        help_text=_("Father, if registered in the herd."),
    )
    sire_external_id = models.CharField(
        _("Sire (External ID)"),
        max_length=100,
        blank=True,
        help_text=_("Father's Name/ID if not in the herd."),
    )
    dam = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offspring_dam",
        verbose_name=_("Dam (Internal)"),
        help_text=_("Mother, if registered in the herd."),
    )
    dam_external_id = models.CharField(
        _("Dam (External ID)"),
        max_length=100,
        blank=True,
        help_text=_("Mother's Name/ID if not in the herd."),
    )

    notes = models.TextField(_("Notes"), blank=True)

    # Weight Cache (Updated by WeightService)
    current_weight = models.DecimalField(
        _("Current Weight (kg)"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    last_weighing_date = models.DateField(
        _("Last Weighing Date"), null=True, blank=True
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

    def delete(self, using=None, keep_parents=False, destroy=False):
        """
        Override delete to check for linked transactions (Sales/Purchases)
        before allowing both Soft and Hard deletes.
        """
        # Check Linked Sales
        ct = ContentType.objects.get_for_model(self)
        if SaleItem.objects.filter(content_type=ct, object_id=self.pk).exists():
            raise ValidationError(
                _(
                    "Cannot delete cattle because it is part of a Sale transaction. Please delete the transaction item first."
                )
            )

        # Check Linked Purchases
        if PurchaseItem.objects.filter(content_type=ct, object_id=self.pk).exists():
            raise ValidationError(
                _(
                    "Cannot delete cattle because it is part of a Purchase transaction. Please delete the transaction item first."
                )
            )

        return super().delete(using=using, keep_parents=keep_parents, destroy=destroy)

    def clean(self):
        super().clean()

        if self.sire and self.sire_external_id:
            raise ValidationError(
                _(
                    "You cannot specify both an internal Sire and an external Sire ID. Please choose one."
                )
            )

        if self.dam and self.dam_external_id:
            raise ValidationError(
                _(
                    "You cannot specify both an internal Dam and an external Dam ID. Please choose one."
                )
            )

        if self.pk:
            if self.sire and self.sire.pk == self.pk:
                raise ValidationError(_("A cattle cannot be its own sire."))
            if self.dam and self.dam.pk == self.pk:
                raise ValidationError(_("A cattle cannot be its own dam."))

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
