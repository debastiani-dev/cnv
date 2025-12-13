from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.cattle.models.cattle import Cattle


class ReproductiveSeason(BaseModel):
    name = models.CharField(
        _("Name"), max_length=100, help_text=_("e.g. Breeding Season 2024/2025")
    )
    start_date = models.DateField(_("Start Date"))
    end_date = models.DateField(_("End Date"), blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Reproductive Season")
        verbose_name_plural = _("Reproductive Seasons")

    def __str__(self):
        return self.name


class BreedingEvent(BaseModel):
    METHOD_AI = "AI"
    METHOD_IATF = "IATF"
    METHOD_NATURAL = "NATURAL"
    METHOD_ET = "ET"

    METHOD_CHOICES = [
        (METHOD_AI, _("Artificial Insemination")),
        (METHOD_IATF, _("Fixed-Time AI")),
        (METHOD_NATURAL, _("Natural Mating")),
        (METHOD_ET, _("Embryo Transfer")),
    ]

    dam = models.ForeignKey(
        Cattle,
        on_delete=models.CASCADE,
        related_name="breeding_events_as_dam",
        verbose_name=_("Dam"),
        limit_choices_to={"sex": Cattle.SEX_FEMALE},
    )
    date = models.DateField(_("Date"))
    breeding_method = models.CharField(
        _("Method"), max_length=20, choices=METHOD_CHOICES, default=METHOD_AI
    )

    sire = models.ForeignKey(
        Cattle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="breeding_events_as_sire",
        verbose_name=_("Sire (Internal)"),
        limit_choices_to={"sex": Cattle.SEX_MALE},
    )
    sire_name = models.CharField(
        _("Sire Name (External)"),
        max_length=100,
        blank=True,
        help_text=_("If sire is not in inventory"),
    )

    batch = models.ForeignKey(
        ReproductiveSeason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="breeding_events",
        verbose_name=_("Season/Batch"),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Breeding Event")
        verbose_name_plural = _("Breeding Events")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.dam} - {self.date} ({self.get_breeding_method_display()})"


class PregnancyCheck(BaseModel):
    RESULT_POSITIVE = "POSITIVE"
    RESULT_NEGATIVE = "NEGATIVE"

    RESULT_CHOICES = [
        (RESULT_POSITIVE, _("Positive")),
        (RESULT_NEGATIVE, _("Negative")),
    ]

    breeding_event = models.ForeignKey(
        BreedingEvent,
        on_delete=models.CASCADE,
        related_name="pregnancy_checks",
        verbose_name=_("Breeding Event"),
    )
    date = models.DateField(_("Check Date"))
    result = models.CharField(_("Result"), max_length=20, choices=RESULT_CHOICES)
    fetus_days = models.PositiveIntegerField(
        _("Fetus Days"),
        blank=True,
        null=True,
        help_text=_("Estimated age of fetus in days"),
    )
    expected_calving_date = models.DateField(
        _("Expected Calving Date"), blank=True, null=True
    )

    @property
    def is_pregnant(self):
        return self.result == self.RESULT_POSITIVE

    class Meta(BaseModel.Meta):
        verbose_name = _("Pregnancy Check")
        verbose_name_plural = _("Pregnancy Checks")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.breeding_event.dam} - {self.get_result_display()}"


class Calving(BaseModel):
    EASE_EASY = "EASY"
    EASE_ASSISTED = "ASSISTED"
    EASE_C_SECTION = "C_SECTION"

    EASE_CHOICES = [
        (EASE_EASY, _("Easy/Unassisted")),
        (EASE_ASSISTED, _("Assisted")),
        (EASE_C_SECTION, _("C-Section")),
    ]

    dam = models.ForeignKey(
        Cattle, on_delete=models.CASCADE, related_name="calvings", verbose_name=_("Dam")
    )
    breeding_event = models.ForeignKey(
        BreedingEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calving_outcome",
        verbose_name=_("Linked Breeding Event"),
    )
    date = models.DateField(_("Calving Date"))
    calf = models.OneToOneField(
        Cattle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="birth_event",
        verbose_name=_("Calf"),
    )
    ease_of_birth = models.CharField(
        _("Ease of Birth"), max_length=20, choices=EASE_CHOICES, default=EASE_EASY
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Calving")
        verbose_name_plural = _("Calvings")
        ordering = ["-date"]

    def __str__(self):
        return f"Calving: {self.dam} on {self.date}"
