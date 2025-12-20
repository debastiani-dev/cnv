from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.partners.models.partner import Partner


class Transaction(BaseModel):
    TYPE_SALE = "SALE"
    TYPE_PURCHASE = "PURCHASE"

    TYPE_CHOICES = [
        (TYPE_SALE, _("Sale / Revenue")),
        (TYPE_PURCHASE, _("Purchase / Expense")),
    ]

    STATUS_DRAFT = "DRAFT"
    STATUS_CONFIRMED = "CONFIRMED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_CONFIRMED, _("Confirmed")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    strict_deletion_ignore_fields = ["items"]

    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name=_("Partner"),
    )

    date = models.DateField(_("Date"))
    type = models.CharField(_("Type"), max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )

    # Financials
    total_amount = models.DecimalField(
        _("Total Amount"), max_digits=12, decimal_places=2, default=0.00
    )

    notes = models.TextField(_("Notes"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        indexes = [
            models.Index(fields=["date", "type"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.partner} - {self.date}"

    def update_total(self):
        """Recalculates total from items"""
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save()
