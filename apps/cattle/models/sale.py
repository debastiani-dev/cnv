from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel

from .cattle import Cattle


class Sale(BaseModel):
    date = models.DateField(_("Sale Date"))
    buyer = models.CharField(_("Buyer"), max_length=255)
    total_price = models.DecimalField(
        _("Total Price"), max_digits=12, decimal_places=2, default=0.00
    )
    notes = models.TextField(_("Notes"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Sale")
        verbose_name_plural = _("Sales")

    def __str__(self):
        return f"Sale on {self.date} to {self.buyer}"


class SaleItem(BaseModel):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Sale"),
    )
    cattle = models.ForeignKey(
        Cattle,
        on_delete=models.PROTECT,
        related_name="sales",
        verbose_name=_("Cattle"),
    )
    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2)

    class Meta(BaseModel.Meta):
        verbose_name = _("Sale Item")
        verbose_name_plural = _("Sale Items")
        unique_together = ("sale", "cattle")

    def __str__(self):
        return f"{self.cattle} in {self.sale}"
