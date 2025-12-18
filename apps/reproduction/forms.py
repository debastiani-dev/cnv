from django import forms
from django.utils.translation import gettext_lazy as _

from apps.cattle.models.cattle import Cattle
from apps.locations.models import Location, LocationType
from apps.locations.services.allocation import AllocationService
from apps.reproduction.models import (
    BreedingEvent,
    Calving,
    MatingPlan,
    ReproductiveSeason,
)


class ReproductiveSeasonForm(forms.ModelForm):
    class Meta:
        model = ReproductiveSeason
        fields = ["name", "start_date", "end_date"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _field_name, field in self.fields.items():
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


TAILWIND_INPUT_CLASS = (
    "block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm "
    "ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 "
    "focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6"
)


class MatingPlanForm(forms.ModelForm):
    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(
            is_active=True, type=LocationType.PASTURE
        ).order_by("name"),
        required=False,
        label=_("Location (Paddock)"),
        help_text=_(
            "Required if setting status to Active. This will move all animals to this paddock."
        ),
    )

    class Meta:
        model = MatingPlan
        fields = ["season", "sire", "cows", "notes", "status"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "cows": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _field_name, field in self.fields.items():
            # CheckboxSelectMultiple needs different styling or just default wrapper validation
            # Location is a select, so it gets the class
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs["class"] = TAILWIND_INPUT_CLASS

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        location = cleaned_data.get("location")
        sire = cleaned_data.get("sire")
        cows = cleaned_data.get("cows")

        if status == MatingPlan.Status.ACTIVE:
            if not location:
                self.add_error(
                    "location", _("You must select a location to activate the plan.")
                )
            elif sire and cows:
                # Gather all animals to be moved
                animals = [sire] + list(cows)

                # Validate the move
                validation = AllocationService.validate_move(location, animals)

                if not validation["valid"]:
                    # If there are errors, block the save
                    for error in validation["errors"]:
                        self.add_error("location", error)

                if validation["warnings"]:
                    # Optional: We could just show warnings but allow save.
                    # For now, let's append them to help text or non-field errors if we wanted to be fancy.
                    # But simpler: Just let them pass if they aren't errors, maybe specificy in help text.
                    pass

        return cleaned_data

    def save(self, commit=True):
        plan = super().save(commit=False)
        if commit:
            plan.save()
            self.save_m2m()  # Save cows relation first

            # Handle Location Move if Active
            location = self.cleaned_data.get("location")
            if plan.status == MatingPlan.Status.ACTIVE and location:
                # Move Sire
                plan.sire.location = location
                plan.sire.save()
                # Move Cows
                plan.cows.update(location=location)

        return plan
