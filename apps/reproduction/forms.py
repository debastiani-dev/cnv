from django import forms
from django.utils.translation import gettext_lazy as _

from apps.cattle.models.cattle import Cattle
from apps.reproduction.models import BreedingEvent, Calving, ReproductiveSeason


class ReproductiveSeasonForm(forms.ModelForm):
    class Meta:
        model = ReproductiveSeason
        fields = ["name", "start_date", "end_date", "active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name == "active":
                field.widget.attrs["class"] = (
                    "h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-600"
                )
            else:
                field.widget.attrs["class"] = (
                    "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
                )


class CalvingForm(forms.ModelForm):
    # Extra fields for the Calf
    calf_tag = forms.CharField(label=_("Calf Tag"), max_length=50)
    calf_name = forms.CharField(label=_("Calf Name"), max_length=100, required=False)
    calf_sex = forms.ChoiceField(
        label=_("Calf Sex"),
        choices=[(Cattle.SEX_MALE, _("Male")), (Cattle.SEX_FEMALE, _("Female"))],
    )
    calf_weight = forms.DecimalField(
        label=_("Birth Weight (kg)"), max_digits=5, decimal_places=2, required=False
    )

    class Meta:
        model = Calving
        fields = ["dam", "breeding_event", "date", "ease_of_birth", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter dams to those likely to calve (Pregnant or Bred)
        self.fields["dam"].queryset = Cattle.objects.filter(
            reproduction_status__in=[Cattle.REP_STATUS_PREGNANT, Cattle.REP_STATUS_BRED]
        ).order_by("tag")

        # Make breeding_event optional in UI (though logic prefers it)
        self.fields["breeding_event"].required = False
        self.fields["breeding_event"].help_text = _(
            "Select the breeding event to link lineage (Sire)."
        )


class BreedingEventForm(forms.ModelForm):
    class Meta:
        model = BreedingEvent
        fields = ["dam", "date", "breeding_method", "sire", "sire_name", "batch"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Tailwind classes to all fields
        for _field_name, field in self.fields.items():
            field.widget.attrs["class"] = (
                "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
            )

        # Specific tweaks
        self.fields["dam"].queryset = Cattle.objects.filter(
            reproduction_status__in=[
                Cattle.REP_STATUS_OPEN,
                Cattle.REP_STATUS_LACTATING,
            ]
        ).order_by("tag")
        self.fields["dam"].help_text = _(  # pylint: disable=undefined-loop-variable
            "Only Open or Lactating females are eligible."
        )

        # Ensure optional fields don't require input (logic handled in view/service)
        self.fields["sire"].required = False
        self.fields["sire_name"].required = False
        self.fields["batch"].required = False
