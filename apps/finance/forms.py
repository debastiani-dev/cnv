from django import forms

from apps.finance.models.finance import CostEntry


class CostEntryForm(forms.ModelForm):
    class Meta:
        model = CostEntry
        fields = [
            "animal",
            "date",
            "category",
            "description",
            "amount",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(attrs={"class": "w-full"}),
        }


class BatchCostForm(CostEntryForm):
    cattle_ids = forms.CharField(widget=forms.HiddenInput())

    class Meta(CostEntryForm.Meta):
        fields = [
            "date",
            "category",
            "description",
            "amount",
        ]
