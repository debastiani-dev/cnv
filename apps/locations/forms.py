from django import forms

from apps.locations.models import Location, Movement


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = [
            "name",
            "type",
            "area_hectares",
            "capacity_head",
            "status",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "type": forms.Select(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "area_hectares": forms.NumberInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    ),
                    "step": "0.01",
                }
            ),
            "capacity_head": forms.NumberInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": (
                        "h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600"
                    )
                }
            ),
        }


class MovementForm(forms.ModelForm):
    cattle_ids = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Movement
        fields = ["destination", "reason", "date", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Custom validation if needed, e.g. checking if cattle_ids are present
        cattle_ids = cleaned_data.get("cattle_ids")
        if not cattle_ids:
            # It might be valid if we populate it differently, but for this form usage we expect IDs
            pass
        return cleaned_data
