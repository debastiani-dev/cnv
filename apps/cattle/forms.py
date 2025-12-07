from django import forms
from apps.cattle.models import Cattle

class CattleForm(forms.ModelForm):
    class Meta:
        model = Cattle
        fields = ["tag", "name", "birth_date", "weight_kg", "breed", "status"]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }
