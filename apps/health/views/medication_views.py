from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.health.forms import MedicationForm
from apps.health.models import Medication
from apps.health.services import HealthService


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


class MedicationTrashListView(LoginRequiredMixin, ListView):
    model = Medication
    template_name = "health/medication_trash_list.html"
    context_object_name = "medications"

    def get_queryset(self):
        return HealthService.get_deleted_medications()


class MedicationRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            HealthService.restore_medication(pk)
            messages.success(request, _("Medication restored successfully."))
        except ValueError as e:
            messages.error(request, str(e))
        except Medication.DoesNotExist:
            messages.error(request, _("Medication not found."))

        return redirect("health:medication-list")

    def get(self, request, pk):
        try:
            medication = Medication.all_objects.get(pk=pk)
            return render(
                request,
                "health/medication_confirm_restore.html",
                {"medication": medication},
            )
        except Medication.DoesNotExist:
            messages.error(request, _("Medication not found."))
            return redirect("health:medication-list")


class MedicationPermanentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            HealthService.hard_delete_medication(pk)
            messages.success(request, _("Medication permanently deleted."))
        except Medication.DoesNotExist:
            messages.error(request, _("Medication not found."))
        except ProtectedError:
            # Need to fetch object to render template if possible, or just error
            try:
                medication = Medication.all_objects.get(pk=pk)
                return render(
                    request,
                    "health/medication_confirm_permanent_delete.html",
                    {
                        "medication": medication,
                        "error": _(
                            "Cannot permanently delete this medication because it is still linked to historical/archived events."
                        ),
                    },
                )
            except Medication.DoesNotExist:
                pass  # Should not happen if we got ProtectedError usually

        return redirect("health:medication-trash")

    def get(self, request, pk):
        try:
            medication = Medication.all_objects.get(pk=pk)
            return render(
                request,
                "health/medication_confirm_permanent_delete.html",
                {"medication": medication},
            )
        except Medication.DoesNotExist:
            messages.error(request, _("Medication not found."))
            return redirect("health:medication-trash")
