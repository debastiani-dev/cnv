from django import forms

from apps.partners.models import Partner


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "name",
            "tax_id",
            "email",
            "phone",
            "is_customer",
            "is_supplier",
            "notes",
        ]
        input_attrs = {
            "class": (
                "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm "
                "ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 "
                "focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 "
                "dark:bg-gray-800 dark:text-white dark:ring-gray-700"
            )
        }
        checkbox_attrs = {
            "class": (
                "h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600 "
                "dark:border-gray-600 dark:bg-gray-700"
            )
        }

        widgets = {
            "name": forms.TextInput(attrs=input_attrs),
            "tax_id": forms.TextInput(attrs=input_attrs),
            "email": forms.EmailInput(attrs=input_attrs),
            "phone": forms.TextInput(attrs=input_attrs),
            "notes": forms.Textarea(attrs={"rows": 3, **input_attrs}),
            "is_customer": forms.CheckboxInput(attrs=checkbox_attrs),
            "is_supplier": forms.CheckboxInput(attrs=checkbox_attrs),
        }
