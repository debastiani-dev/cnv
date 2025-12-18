from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import BaseModel
from apps.cattle.models import Cattle
from apps.reproduction.models.reproduction import ReproductiveSeason


class MatingPlan(BaseModel):
    """
    Plan a specific mating between a Sire (Bull) and a Batch of Cows.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        APPROVED_WAITING = "APPROVED_WAITING", _("Approved (Waiting for Location)")
        ACTIVE = "ACTIVE", _("Active (In Paddock)")
        COMPLETED = "COMPLETED", _("Completed")

    season = models.ForeignKey(
        ReproductiveSeason,
        on_delete=models.CASCADE,
        related_name="mating_plans",
        verbose_name=_("Season"),
    )
    sire = models.ForeignKey(
        Cattle,
        on_delete=models.PROTECT,
        related_name="mating_plans",
        limit_choices_to={"sex": Cattle.SEX_MALE},
        verbose_name=_("Sire"),
    )
    # We reference a list of cows. For simplicity, M2M directly to Cattle.
    # In a real batch system, this might be a CattleBatch model.
    # Based on the prompt: "Batch of Cows".
    cows = models.ManyToManyField(
        Cattle,
        related_name="assigned_mating_plans",
        verbose_name=_("Cows"),
        limit_choices_to={"sex": Cattle.SEX_FEMALE},
    )
    status = models.CharField(
        _("Status"), max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta:
        verbose_name = _("Mating Plan")
        verbose_name_plural = _("Mating Plans")
        ordering = ["-season", "sire__name"]

    def __str__(self):
        return f"{self.sire.name} - {self.season.name}"


class MatingExclusion(BaseModel):
    """
    Explicitly forbids mating between two animals (or lines).
    """

    animal_a = models.ForeignKey(
        Cattle,
        on_delete=models.CASCADE,
        related_name="exclusions_as_a",
        verbose_name=_("Animal A"),
    )
    animal_b = models.ForeignKey(
        Cattle,
        on_delete=models.CASCADE,
        related_name="exclusions_as_b",
        verbose_name=_("Animal B"),
    )
    reason = models.CharField(_("Reason"), max_length=200)

    class Meta:
        verbose_name = _("Mating Exclusion")
        verbose_name_plural = _("Mating Exclusions")
        unique_together = ("animal_a", "animal_b")

    def __str__(self):
        return f"Exclusion: {self.animal_a} x {self.animal_b}"
