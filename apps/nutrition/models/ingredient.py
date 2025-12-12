from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models import BaseModel


class FeedIngredient(BaseModel):
    name = models.CharField(_("Name"), max_length=100)
    stock_quantity = models.DecimalField(
        _("Stock Quantity (kg)"), max_digits=10, decimal_places=2, default=0
    )
    unit_cost = models.DecimalField(
        _("Unit Cost ($/kg)"), max_digits=10, decimal_places=2, default=0
    )
    min_stock_alert = models.DecimalField(
        _("Low Stock Alert (kg)"), max_digits=10, decimal_places=2, default=0
    )

    class Meta:
        verbose_name = _("Feed Ingredient")
        verbose_name_plural = _("Feed Ingredients")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.stock_quantity} kg)"
