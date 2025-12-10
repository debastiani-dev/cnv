from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView

from apps.reproduction.forms import CalvingForm
from apps.reproduction.models import Calving
from apps.reproduction.services.reproduction_service import ReproductionService


class CalvingListView(ListView):
    model = Calving
    template_name = "reproduction/calving_list.html"
    context_object_name = "calvings"
    paginate_by = 20

    def get_queryset(self):
        return Calving.objects.select_related("dam", "calf").order_by("-date")


class CalvingCreateView(CreateView):
    model = Calving
    form_class = CalvingForm
    template_name = "reproduction/calving_form.html"
    success_url = reverse_lazy("reproduction:calving_list")

    def form_valid(self, form):
        try:
            calf_data = {
                "tag": form.cleaned_data["calf_tag"],
                "name": form.cleaned_data["calf_name"],
                "sex": form.cleaned_data["calf_sex"],
                "weight_kg": form.cleaned_data["calf_weight"],
            }

            ReproductionService.register_birth(
                dam=form.cleaned_data["dam"],
                date=form.cleaned_data["date"],
                breeding_event=form.cleaned_data["breeding_event"],
                calf_data=calf_data,
                ease_of_birth=form.cleaned_data["ease_of_birth"],
                notes=form.cleaned_data["notes"],
            )
            messages.success(
                self.request, _("Calving recorded and new Calf registered.")
            )
            return redirect(self.success_url)
        except (ValueError, ValidationError) as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)
