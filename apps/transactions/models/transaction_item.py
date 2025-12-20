from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.base.utils.money import Money
from apps.transactions.models.transaction import Transaction


class TransactionItem(BaseModel):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Transaction"),
    )

    # Universal Link (The "Product" being bought/sold)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")

    quantity = models.DecimalField(
        _("Quantity"), max_digits=10, decimal_places=2, default=1
    )
    unit_price = models.DecimalField(_("Unit Price"), max_digits=12, decimal_places=2)
    total_price = models.DecimalField(_("Total Price"), max_digits=12, decimal_places=2)

    class Meta(BaseModel.Meta):
        verbose_name = _("Transaction Item")
        verbose_name_plural = _("Transaction Items")

    def save(self, *args, **kwargs):
        # Enforce Money class precision
        self.total_price = Money(self.quantity) * Money(self.unit_price)
        super().save(*args, **kwargs)

        # Auto-update header total
        # (Ideally move to a signal, but method call works for simple apps)
        self.transaction.update_total()

    def __str__(self):
        return f"{self.quantity}x {self.content_object} in {self.transaction}"
