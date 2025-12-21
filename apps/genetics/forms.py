from django import forms

from apps.cattle.models.cattle import Cattle
from apps.genetics.models import EmbryoBatch, SemenBatch, StorageTank


class StorageTankForm(forms.ModelForm):
    class Meta:
        model = StorageTank
        fields = [
            "name",
            "serial_number",
            "location_description",
            "capacity_liters",
            "last_refill_date",
        ]
        widgets = {
            "last_refill_date": forms.DateInput(attrs={"type": "date"}),
        }


class SemenBatchForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["bull"].queryset = Cattle.objects.filter(sex=Cattle.SEX_MALE)

    class Meta:
        model = SemenBatch
        fields = [
            "bull",
            "bull_name_external",
            "registration_number",
            "breed",
            "type",
            "batch_code",
            "tank",
            "canister",
            "initial_quantity",
            "current_quantity",
            "min_stock_alert",
            "purchase_date",
            "cost_per_unit",
            "supplier",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
        }


class EmbryoBatchForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["sire"].queryset = Cattle.objects.filter(sex=Cattle.SEX_MALE)
        self.fields["dam"].queryset = Cattle.objects.filter(sex=Cattle.SEX_FEMALE)

    class Meta:
        model = EmbryoBatch
        fields = [
            "sire",
            "sire_name",
            "dam",
            "dam_name",
            "grade",
            "stage",
            "tank",
            "canister",
            "initial_quantity",
            "current_quantity",
            "min_stock_alert",
            "purchase_date",
            "cost_per_unit",
            "supplier",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
        }


class StockAdjustmentForm(forms.Form):
    """Form for adjusting genetic material stock quantities."""

    ADJUSTMENT_LOSS = "LOSS"
    ADJUSTMENT_FOUND = "FOUND"

    ADJUSTMENT_TYPE_CHOICES = [
        (ADJUSTMENT_LOSS, "Loss (dropped/damaged)"),
        (ADJUSTMENT_FOUND, "Found (recount adjustment)"),
    ]

    adjustment_type = forms.ChoiceField(
        label="Adjustment Type",
        choices=ADJUSTMENT_TYPE_CHOICES,
        widget=forms.RadioSelect,
    )
    quantity = forms.IntegerField(
        label="Quantity",
        min_value=1,
        help_text="Number of doses/units to adjust",
    )

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = batch

    def clean(self):
        cleaned_data = super().clean()
        adjustment_type = cleaned_data.get("adjustment_type")
        quantity = cleaned_data.get("quantity")

        if adjustment_type == self.ADJUSTMENT_LOSS and self.batch:
            if quantity and quantity > self.batch.current_quantity:
                raise forms.ValidationError(
                    f"Cannot remove {quantity} units. Only {self.batch.current_quantity} units available."
                )

        return cleaned_data

    def apply_adjustment(self):
        """Apply the stock adjustment to the batch."""
        if not self.batch:
            return

        adjustment_type = self.cleaned_data["adjustment_type"]
        quantity = self.cleaned_data["quantity"]

        if adjustment_type == self.ADJUSTMENT_LOSS:
            self.batch.current_quantity -= quantity
        elif adjustment_type == self.ADJUSTMENT_FOUND:
            self.batch.current_quantity += quantity

        self.batch.save(update_fields=["current_quantity"])
