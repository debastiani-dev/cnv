from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.base.utils.money import Money


class CostEntry(BaseModel):
    CATEGORY_NUTRITION = "NUTRITION"
    CATEGORY_HEALTH = "HEALTH"
    CATEGORY_REPRODUCTION = "REPRODUCTION"
    CATEGORY_INDIRECT = "INDIRECT"

    CATEGORY_CHOICES = [
        (CATEGORY_NUTRITION, _("Nutrition")),
        (CATEGORY_HEALTH, _("Health")),
        (CATEGORY_REPRODUCTION, _("Reproduction")),
        (CATEGORY_INDIRECT, _("Indirect/Overhead")),
    ]

    animal = models.ForeignKey(
        "cattle.Cattle",
        on_delete=models.CASCADE,
        related_name="costs",
        verbose_name=_("Animal"),
    )
    date = models.DateField(_("Date"))
    category = models.CharField(_("Category"), max_length=20, choices=CATEGORY_CHOICES)
    description = models.CharField(_("Description"), max_length=255)

    # Storage: Max digits 12, 2 decimal places. stored as 1250.50
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)

    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.UUIDField(_("Object ID"), null=True, blank=True)
    source_event = GenericForeignKey("content_type", "object_id")

    class Meta(BaseModel.Meta):
        verbose_name = _("Cost Entry")
        verbose_name_plural = _("Cost Entries")
        ordering = ["-date"]

    @property
    def money_value(self):
        """Returns the amount wrapped in the Money VO for display/math"""
        return Money(self.amount)

    def save(self, *args, **kwargs):
        # The Money class handles the rounding before DB storage
        if self.amount is not None:
            self.amount = Money(self.amount)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} - {self.get_category_display()} - {str(self.money_value)}"
