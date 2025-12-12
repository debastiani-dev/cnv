from django import forms
from django.forms import inlineformset_factory

from apps.nutrition.models import Diet, DietItem, FeedingEvent, FeedIngredient


class FeedIngredientForm(forms.ModelForm):
    class Meta:
        model = FeedIngredient
        fields = ["name", "stock_quantity", "unit_cost", "min_stock_alert"]


class DietForm(forms.ModelForm):
    class Meta:
        model = Diet
        fields = ["name", "description"]


class DietItemForm(forms.ModelForm):
    class Meta:
        model = DietItem
        fields = ["ingredient", "proportion_percent"]


DietItemFormSet = inlineformset_factory(
    Diet,
    DietItem,
    form=DietItemForm,
    extra=1,
    can_delete=True,
)


class FeedingEventForm(forms.ModelForm):
    class Meta:
        model = FeedingEvent
        fields = ["date", "location", "diet", "amount_kg"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }
