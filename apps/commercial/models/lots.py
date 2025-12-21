from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.cattle.models import Cattle
from apps.transactions.models import TransactionItem

from .events import SalesEvent


class SalesLot(BaseModel):
    """
    The Commercial Product.
    Acts as a wrapper around 1 or more animals.
    """

    STATUS_AVAILABLE = "AVAILABLE"
    STATUS_SOLD = "SOLD"
    STATUS_PASSED = "PASSED"
    STATUS_WITHDRAWN = "WITHDRAWN"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, _("Available")),
        (STATUS_SOLD, _("Sold")),
        (STATUS_PASSED, _("Passed/Unsold")),
        (STATUS_WITHDRAWN, _("Withdrawn")),
    ]

    event = models.ForeignKey(
        SalesEvent,
        on_delete=models.CASCADE,
        related_name="lots",
        verbose_name=_("Event"),
    )

    # FLEXIBILITY: Supports single Bull or Pen of 50 Heifers
    animals = models.ManyToManyField(
        Cattle, related_name="sales_lots", verbose_name=_("Animals")
    )

    lot_number = models.PositiveIntegerField(_("Lot #"))

    # Pricing Strategy (TOTAL for the Lot, not per head)
    # We snapshot cost here to analyze "Projected Margin"
    cost_at_creation = models.DecimalField(
        _("Total Cost Basis"), max_digits=12, decimal_places=2
    )
    reserve_price = models.DecimalField(
        _("Total Reserve Price"), max_digits=12, decimal_places=2
    )

    status = models.CharField(
        _("Status"), max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE
    )

    # The Link to the Legal Ledger
    # Allows us to find the Invoice Line Item associated with this Lot
    transaction_items = GenericRelation(TransactionItem, related_query_name="sales_lot")

    class Meta(BaseModel.Meta):
        unique_together = ["event", "lot_number"]
        ordering = ["event", "lot_number"]
        verbose_name = _("Sales Lot")
        verbose_name_plural = _("Sales Lots")

    def __str__(self):
        # Dynamic string representation
        return f"Lot {self.lot_number} ({self.event.name})"

    @property
    def average_weight(self):
        """Calculates average weight of animals in the lot."""
        count = self.animals.count()
        if count == 0:
            return 0
        total_weight = sum(a.current_weight or 0 for a in self.animals.all())
        val = total_weight / count
        return round(val, 1)
