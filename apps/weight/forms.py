from django import forms

from apps.weight.models import WeighingSession, WeightRecord


class WeighingSessionForm(forms.ModelForm):
    class Meta:
        model = WeighingSession
        fields = ["date", "name", "session_type", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class WeightRecordForm(forms.ModelForm):
    class Meta:
        model = WeightRecord
        fields = ["weight_kg"]
        widgets = {
            "weight_kg": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
        }
