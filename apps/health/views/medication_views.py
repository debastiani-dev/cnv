from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.health.forms import MedicationForm
from apps.health.models import Medication


class MedicationListView(LoginRequiredMixin, ListView):
    model = Medication
    template_name = "health/medication_list.html"
    context_object_name = "medications"
    paginate_by = 10


class MedicationCreateView(LoginRequiredMixin, CreateView):
    model = Medication
    form_class = MedicationForm
    template_name = "health/medication_form.html"
    success_url = reverse_lazy("health:medication-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Add Medication")
        return context


class MedicationUpdateView(LoginRequiredMixin, UpdateView):
    model = Medication
    form_class = MedicationForm
    template_name = "health/medication_form.html"
    success_url = reverse_lazy("health:medication-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Medication")
        return context


class MedicationDeleteView(LoginRequiredMixin, DeleteView):
    model = Medication
    template_name = "health/medication_confirm_delete.html"
    success_url = reverse_lazy("health:medication-list")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request,
                _(
                    "Cannot delete this medication because it is linked to existing sanitary events."
                ),
            )
            return redirect("health:medication-list")
