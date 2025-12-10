from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView

from apps.cattle.models.cattle import Cattle
from apps.reproduction.models import BreedingEvent, PregnancyCheck
from apps.reproduction.services.reproduction_service import ReproductionService


class DiagnosisListView(ListView):
    model = PregnancyCheck
    template_name = "reproduction/pregnancy_check_list.html"
    context_object_name = "checks"
    paginate_by = 20

    def get_queryset(self):
        return PregnancyCheck.objects.select_related("breeding_event__dam").order_by(
            "-date"
        )


class DiagnosisCreateView(CreateView):
    model = PregnancyCheck
    fields = ["breeding_event", "date", "result", "fetus_days"]
    template_name = "reproduction/pregnancy_check_form.html"
    success_url = reverse_lazy("reproduction:diagnosis_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Limit choices to cows that are BRED (and thus waiting for diagnosis)
        # Or maybe allow re-checking pregnant ones? For MVP, BRED is safest default.
        form.fields["breeding_event"].queryset = (
            BreedingEvent.objects.filter(
                dam__reproduction_status=Cattle.REP_STATUS_BRED
            )
            .select_related("dam")
            .order_by("-date")
        )
        # Improved label for dropdown in form/model would be nice (__str__ handles it)
        return form

    def form_valid(self, form):
        try:
            ReproductionService.record_diagnosis(
                breeding_event=form.cleaned_data["breeding_event"],
                date=form.cleaned_data["date"],
                result=form.cleaned_data["result"],
                fetus_days=form.cleaned_data["fetus_days"],
            )
            messages.success(self.request, _("Diagnosis recorded successfully."))
            return redirect(self.success_url)
        except (ValueError, ValidationError) as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
