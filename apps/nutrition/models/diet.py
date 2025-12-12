from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import BaseModel
from apps.nutrition.models.ingredient import FeedIngredient


class Diet(BaseModel):
    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True, null=True)

    class Meta:
        verbose_name = _("Diet")
        verbose_name_plural = _("Diets")
        ordering = ["name"]

    def __str__(self):
        return self.name


class DietItem(BaseModel):
    diet = models.ForeignKey(
        Diet, on_delete=models.CASCADE, related_name="items", verbose_name=_("Diet")
    )
    ingredient = models.ForeignKey(
        FeedIngredient,
        on_delete=models.PROTECT,
        related_name="diet_items",
        verbose_name=_("Ingredient"),
    )
    proportion_percent = models.DecimalField(
        _("Proportion (%)"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Percentage of the diet definition."),
    )

    class Meta:
        verbose_name = _("Diet Item")
        verbose_name_plural = _("Diet Items")
        unique_together = ["diet", "ingredient"]

    def __str__(self):
        return f"{self.ingredient.name} ({self.proportion_percent}%)"
