from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView

from apps.reproduction.models import BreedingEvent
from apps.reproduction.services.reproduction_service import ReproductionService


class BreedingListView(ListView):
    model = BreedingEvent
    template_name = "reproduction/breeding_event_list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        return BreedingEvent.objects.select_related("dam", "sire", "batch").order_by(
            "-date"
        )


class BreedingCreateView(CreateView):
    model = BreedingEvent
    fields = ["dam", "date", "breeding_method", "sire", "sire_name", "batch"]
    template_name = "reproduction/breeding_event_form.html"
    success_url = reverse_lazy("reproduction:breeding_list")

    def form_valid(self, form):
        try:
            ReproductionService.record_breeding(
                dam=form.cleaned_data["dam"],
                date=form.cleaned_data["date"],
                method=form.cleaned_data["breeding_method"],
                sire=form.cleaned_data["sire"],
                sire_name=form.cleaned_data["sire_name"],
                batch=form.cleaned_data["batch"],
            )
            messages.success(self.request, _("Breeding recorded successfully."))
            return redirect(self.success_url)
        except (ValueError, ValidationError) as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
