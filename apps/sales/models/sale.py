from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.base.utils.money import Money
from apps.partners.models.partner import Partner


class Sale(BaseModel):
    TYPE_SALE = "sale"
    TYPE_PURCHASE = "purchase"
    TYPE_CHOICES = [
        (TYPE_SALE, _("Sale")),
        (TYPE_PURCHASE, _("Purchase")),
    ]

    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        verbose_name=_("Partner"),
        related_name="sales",
    )
    date = models.DateField(_("Date"))
    type = models.CharField(
        _("Type"), max_length=20, choices=TYPE_CHOICES, default=TYPE_SALE
    )

    total_amount = models.DecimalField(
        _("Total Amount"), max_digits=12, decimal_places=2, default=0.00
    )

    notes = models.TextField(_("Notes"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self):
        return f"{self.get_type_display()} - {self.partner} - {self.date}"


class SaleItem(BaseModel):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("Transaction"),
    )

    # Generic Foreign Key
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.UUIDField()  # Assuming all our models use UUIDs from BaseModel
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

        # Use Money to calculate total price to ensure consistent rounding
        total = Money(self.quantity) * Money(self.unit_price)
        self.total_price = total
        super().save(*args, **kwargs)
        # TODO: Trigger signal to update Sale total # pylint: disable=fixme

    def __str__(self):
        return f"{self.quantity}x {self.content_object} in {self.sale}"
