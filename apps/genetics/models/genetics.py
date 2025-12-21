from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel
from apps.cattle.models import Cattle
from apps.partners.models import Partner


class StorageTank(BaseModel):
    """
    Physical Nitrogen Tank.
    """

    name = models.CharField(_("Tank Name"), max_length=50)
    serial_number = models.CharField(_("Serial Number"), max_length=50, blank=True)
    location_description = models.CharField(_("Physical Location"), max_length=100)
    capacity_liters = models.DecimalField(
        _("Capacity (L)"), max_digits=5, decimal_places=1
    )
    last_refill_date = models.DateField(_("Last N2 Refill"), null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Storage Tank")
        verbose_name_plural = _("Storage Tanks")


class GeneticBase(BaseModel):
    """
    Abstract base class for genetic material.
    """

    tank = models.ForeignKey(
        StorageTank, on_delete=models.PROTECT, related_name="%(class)s_contents"
    )
    canister = models.CharField(
        _("Canister/Cane"),
        max_length=50,
        help_text="e.g. Canister 3, Cane Blue",
    )

    # Inventory
    initial_quantity = models.PositiveIntegerField(_("Initial Doses/Qty"))
    current_quantity = models.PositiveIntegerField(_("Current Doses/Qty"))
    min_stock_alert = models.PositiveIntegerField(_("Min Stock Alert"), default=10)

    # Financials
    purchase_date = models.DateField(_("Purchase/Collection Date"))
    cost_per_unit = models.DecimalField(
        _("Cost per Unit"), max_digits=10, decimal_places=2
    )
    supplier = models.ForeignKey(
        Partner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Supplier"),
    )

    class Meta:
        abstract = True


class SemenBatch(GeneticBase):
    """
    A batch of Semen Straws from a specific Bull.
    """

    TYPE_CONVENTIONAL = "CONVENTIONAL"
    TYPE_SEXED_MALE = "SEXED_MALE"
    TYPE_SEXED_FEMALE = "SEXED_FEMALE"

    bull = models.ForeignKey(
        Cattle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="semen_batches",
        help_text="Link if the bull is in our system",
    )
    bull_name_external = models.CharField(
        _("Bull Name (Ext)"), max_length=100, blank=True
    )
    registration_number = models.CharField(_("RGN"), max_length=50, blank=True)
    breed = models.CharField(_("Breed"), max_length=50, default="Nelore")

    type = models.CharField(
        max_length=20,
        choices=[
            (TYPE_CONVENTIONAL, "Conventional"),
            (TYPE_SEXED_MALE, "Sexed (Male)"),
            (TYPE_SEXED_FEMALE, "Sexed (Female)"),
        ],
        default=TYPE_CONVENTIONAL,
    )

    batch_code = models.CharField(_("Batch Code"), max_length=50, blank=True)

    # Generic Relations for Transactions and Sales
    transaction_items = GenericRelation(
        "transactions.TransactionItem",
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="semen_batch",
    )
    sales_lots = GenericRelation(
        "commercial.SalesLot",
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="semen_batch",
    )

    def __str__(self):
        name = self.bull.tag if self.bull else self.bull_name_external
        return f"Semen: {name} ({self.get_type_display()})"

    class Meta:
        verbose_name = _("Semen Batch")
        verbose_name_plural = _("Semen Batches")


class EmbryoBatch(GeneticBase):
    """
    Frozen Embryos (TE or IVF).
    """

    sire = models.ForeignKey(
        Cattle,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="embryos_sired",
        verbose_name=_("Sire (Internal)"),
        help_text=_("Link if the sire is in our system"),
    )
    sire_name = models.CharField(_("Sire (Ext/Name)"), max_length=100, blank=True)

    dam = models.ForeignKey(
        Cattle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="embryos_dammed",
        verbose_name=_("Dam (Internal)"),
        help_text=_("Link if the dam is in our system"),
    )
    dam_name = models.CharField(_("Dam (Ext/Name)"), max_length=100, blank=True)

    grade = models.CharField(
        _("Quality Grade"),
        max_length=10,
        choices=[("1", "Grade 1"), ("2", "Grade 2")],
    )
    stage = models.CharField(_("Stage"), max_length=20, default="Blastocyst")

    # Generic Relations for Transactions and Sales
    transaction_items = GenericRelation(
        "transactions.TransactionItem",
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="embryo_batch",
    )
    sales_lots = GenericRelation(
        "commercial.SalesLot",
        content_type_field="content_type",
        object_id_field="object_id",
        related_query_name="embryo_batch",
    )

    def __str__(self):
        return f"Embryo: {self.sire_name} x {self.dam_name}"

    class Meta:
        verbose_name = _("Embryo Batch")
        verbose_name_plural = _("Embryo Batches")
