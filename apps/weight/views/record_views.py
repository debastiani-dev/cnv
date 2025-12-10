from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, UpdateView

from apps.weight.forms import WeightRecordForm
from apps.weight.models import WeightRecord


class WeightRecordUpdateView(LoginRequiredMixin, UpdateView):
    model = WeightRecord
    form_class = WeightRecordForm
    template_name = "weight/record_form.html"

    def get_success_url(self):
        return reverse_lazy(
            "weight:session-detail", kwargs={"pk": self.object.session.pk}
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Weight Record")
        return context

    def form_valid(self, form):
        # We might need to recalculate ADG if weight changed.
        # The save() method of model or service should handle logic,
        # but here we are using standard UpdateView which calls form.save().
        # Ideally, we should use Service.
        response = super().form_valid(form)

        # Trigger ADG recalculation logic if needed.
        # For now, let's assume the simplified logic:
        # If we want to be strict, we call WeightService.record_weight logic again?
        # But that creates a new record. We are UPDATING.
        # Let's rely on standard save for now, but note that ADG might need manual recalc
        # if we are changing PAST records.
        # However, for simplicity in this iteration:
        messages.success(self.request, _("Weight record updated."))
        return response


class WeightRecordDeleteView(LoginRequiredMixin, DeleteView):
    model = WeightRecord
    template_name = "weight/record_confirm_delete.html"

    def get_success_url(self):
        return reverse_lazy(
            "weight:session-detail", kwargs={"pk": self.object.session.pk}
        )

    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        session = self.object.session

        if session.records.count() <= 1:
            messages.error(
                request, _("Cannot delete the last record in a weighing session.")
            )
            return redirect(success_url)

        self.object.delete()
        messages.success(request, _("Weight record deleted."))
        return redirect(success_url)
