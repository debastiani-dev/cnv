from django.db import models
from django.db.models import ProtectedError
from django.utils.translation import gettext_lazy as _

from apps.authentication.models.user import User
from apps.base.models.base_model import BaseModel
from apps.cattle.models.cattle import Cattle


class MedicationType(models.TextChoices):
    VACCINE = "VACCINE", _("Vaccine")
    ANTIBIOTIC = "ANTIBIOTIC", _("Antibiotic")
    VERMIFUGE = "VERMIFUGE", _("Vermifuge/Dewormer")
    SUPPLEMENT = "SUPPLEMENT", _("Supplement/Vitamin")
    HORMONE = "HORMONE", _("Hormone")
    EXAM = "EXAM", _("Exam/Diagnosis")
    OTHER = "OTHER", _("Other")


class MedicationUnit(models.TextChoices):
    ML = "ML", _("Milliliters (ml)")
    DOSE = "DOSE", _("Doses")
    GRAM = "GRAM", _("Grams (g)")
    MG = "MG", _("Milligrams (mg)")
    PILL = "PILL", _("Pills/Tablets")
    UNIT = "UNIT", _("Units")


class Medication(BaseModel):
    """
    Registry of medicines and health products.
    """

    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    medication_type = models.CharField(
        _("Type"),
        max_length=20,
        choices=MedicationType.choices,
        default=MedicationType.OTHER,
    )
    unit = models.CharField(
        _("Unit"),
        max_length=10,
        choices=MedicationUnit.choices,
        default=MedicationUnit.ML,
    )
    manufacturer = models.CharField(_("Manufacturer"), max_length=100, blank=True)
    batch_number = models.CharField(_("Batch Number"), max_length=50, blank=True)
    expiration_date = models.DateField(_("Expiration Date"), null=True, blank=True)

    active_ingredient = models.CharField(
        _("Active Ingredient"), max_length=100, blank=True
    )

    withdrawal_days_meat = models.PositiveIntegerField(
        _("Withdrawal (Meat)"), default=0, help_text=_("Days until safe for slaughter.")
    )
    withdrawal_days_milk = models.PositiveIntegerField(
        _("Withdrawal (Milk)"), default=0, help_text=_("Days until milk is safe.")
    )

    notes = models.TextField(_("Notes"), blank=True)

    default_dose = models.DecimalField(
        _("Default Dose"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Standard dose amount per animal"),
    )

    class Meta:
        verbose_name = _("Medication")
        verbose_name_plural = _("Medications")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_medication_type_display()})"

    def delete(self, *args, **kwargs):
        # Check for related SanitaryEvents (even soft-deleted ones)
        # If destroy=True, Django's on_delete=models.PROTECT handles it (DB integrity).
        # If destroy=False (soft delete), we must check manually.
        if not kwargs.get("destroy", False):
            if self.events.exists():
                raise ProtectedError(
                    _(
                        "Cannot delete this medication because it has been used in sanitary events (active or archived)."
                    ),
                    self.events.all(),
                )
        return super().delete(*args, **kwargs)


class SanitaryEvent(BaseModel):
    """
    Represents a health event performed on a group of animals (or single animal).
    e.g., 'Routine Foot-and-Mouth Vaccination'.
    """

    date = models.DateField(_("Date of Event"))
    title = models.CharField(_("Event Title"), max_length=150)
    notes = models.TextField(_("Notes/Observation"), blank=True)

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sanitary_events",
        verbose_name=_("Performed By"),
    )

    # Medication is optional (e.g. for procedures like dehorning)
    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="events",
        verbose_name=_("Medication/Product"),
    )

    total_cost = models.DecimalField(
        _("Total Event Cost"), max_digits=10, decimal_places=2, default=0.00
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = _("Sanitary Event")
        verbose_name_plural = _("Sanitary Events")

    # Ignore targets for strict deletion check (they are composition pieces, cascade deleted)
    strict_deletion_ignore_fields = ["targets"]

    def __str__(self):
        return f"{self.date} - {self.title}"


class SanitaryEventTarget(BaseModel):
    """
    Links a specific animal to an event (The 'Detail' record).
    """

    event = models.ForeignKey(
        SanitaryEvent,
        on_delete=models.CASCADE,
        related_name="targets",
        verbose_name=_("Event"),
    )
    animal = models.ForeignKey(
        Cattle,
        on_delete=models.CASCADE,
        related_name="health_records",
        verbose_name=_("Animal"),
    )

    applied_dose = models.DecimalField(
        _("Applied Dose"), max_digits=8, decimal_places=2, null=True, blank=True
    )
    cost_per_head = models.DecimalField(
        _("Cost per Head"), max_digits=10, decimal_places=2, default=0.00
    )

    observation = models.CharField(_("Observation"), max_length=255, blank=True)

    class Meta:
        verbose_name = _("Sanitary Event Target")
        verbose_name_plural = _("Sanitary Event Targets")
        constraints = [
            models.UniqueConstraint(
                fields=["event", "animal"],
                name="unique_animal_per_event",
                condition=models.Q(is_deleted=False),
            )
        ]

    def __str__(self):
        return f"{self.animal} - {self.event.title}"
