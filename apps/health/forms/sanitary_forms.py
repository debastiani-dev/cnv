from django import forms

from apps.health.forms.constants import (
    DATE_INPUT_ATTRS,
    NUMBER_INPUT_ATTRS,
    SELECT_ATTRS,
    TEXT_INPUT_ATTRS,
    TEXTAREA_ATTRS,
)
from apps.health.models import Medication, SanitaryEvent


class SanitaryEventForm(forms.ModelForm):
    # Use a custom widget for date if not using a library
    date = forms.DateField(widget=forms.DateInput(attrs=DATE_INPUT_ATTRS))

    class Meta:
        model = SanitaryEvent
        fields = ["date", "title", "medication", "total_cost", "notes"]
        widgets = {
            "title": forms.TextInput(attrs=TEXT_INPUT_ATTRS),
            "medication": forms.Select(attrs=SELECT_ATTRS),
            "total_cost": forms.NumberInput(
                attrs={**NUMBER_INPUT_ATTRS, "step": "0.01"}
            ),
            "notes": forms.Textarea(attrs=TEXTAREA_ATTRS),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize labels or required states if needed
        self.fields["medication"].queryset = Medication.objects.all()
        self.fields["medication"].empty_label = "--- No Medication (Procedure Only) ---"


class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = [
            "name",
            "manufacturer",
            "batch_number",
            "expiration_date",
            "withdrawal_days_meat",
            "withdrawal_days_milk",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs=TEXT_INPUT_ATTRS),
            "manufacturer": forms.TextInput(attrs=TEXT_INPUT_ATTRS),
            "batch_number": forms.TextInput(attrs=TEXT_INPUT_ATTRS),
            "expiration_date": forms.DateInput(attrs=DATE_INPUT_ATTRS),
            "withdrawal_days_meat": forms.NumberInput(attrs=NUMBER_INPUT_ATTRS),
            "withdrawal_days_milk": forms.NumberInput(attrs=NUMBER_INPUT_ATTRS),
            "notes": forms.Textarea(attrs=TEXTAREA_ATTRS),
        }
