from django import forms

from .models import Medication, SanitaryEvent


class SanitaryEventForm(forms.ModelForm):
    # Use a custom widget for date if not using a library
    date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": (
                    "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                ),
            }
        )
    )

    class Meta:
        model = SanitaryEvent
        fields = ["date", "title", "medication", "total_cost", "notes"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "medication": forms.Select(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "total_cost": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    ),
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    ),
                }
            ),
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
            "name": forms.TextInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "manufacturer": forms.TextInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "batch_number": forms.TextInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "expiration_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    ),
                }
            ),
            "withdrawal_days_meat": forms.NumberInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "withdrawal_days_milk": forms.NumberInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    )
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": (
                        "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                    ),
                }
            ),
        }
