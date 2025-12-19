from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.base.views.mixins import HandleProtectedErrorMixin
from apps.cattle.models import Cattle
from apps.finance.forms import CostEntryForm
from apps.finance.models.finance import CostEntry
from apps.finance.services.costing import CostingService

CATTLE_DETAIL_URL = "cattle:detail"
TAB_FINANCIAL_PARAM = "?tab=financial"


class CostEntryListView(LoginRequiredMixin, ListView):
    model = CostEntry
    template_name = "finance/cost_list.html"
    context_object_name = "costs"
    paginate_by = 20

    def get_queryset(self):
        return CostingService.get_all_costs()


class CostEntryCreateView(LoginRequiredMixin, CreateView):
    model = CostEntry
    form_class = CostEntryForm
    template_name = "finance/cost_form.html"

    def get_initial(self):
        initial = super().get_initial()
        animal_id = self.request.GET.get("animal")
        if animal_id:
            try:
                animal = Cattle.objects.get(pk=animal_id)
                initial["animal"] = animal
            except Cattle.DoesNotExist:
                pass
        return initial

    def get_success_url(self):
        # Redirect to animal detail if created from there
        if self.object.animal:
            return (
                reverse_lazy(CATTLE_DETAIL_URL, kwargs={"pk": self.object.animal.pk})
                + TAB_FINANCIAL_PARAM
            )
        return reverse_lazy("finance:cost-list")

    def form_valid(self, form):
        self.object = CostingService.create_cost(form.cleaned_data)
        messages.success(self.request, _("Cost entry created successfully."))
        return HttpResponseRedirect(self.get_success_url())


class CostEntryUpdateView(LoginRequiredMixin, UpdateView):
    model = CostEntry
    form_class = CostEntryForm
    template_name = "finance/cost_form.html"

    def get_success_url(self):
        if self.object.animal:
            return (
                reverse_lazy(CATTLE_DETAIL_URL, kwargs={"pk": self.object.animal.pk})
                + TAB_FINANCIAL_PARAM
            )
        return reverse_lazy("finance:cost-list")

    def form_valid(self, form):
        self.object = CostingService.update_cost(self.object, form.cleaned_data)
        messages.success(self.request, _("Cost entry updated successfully."))
        return HttpResponseRedirect(self.get_success_url())


class CostEntryDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView):
    model = CostEntry
    template_name = "finance/cost_confirm_delete.html"

    def get_success_url(self):
        if self.object.animal:
            return (
                reverse_lazy(CATTLE_DETAIL_URL, kwargs={"pk": self.object.animal.pk})
                + TAB_FINANCIAL_PARAM
            )
        return reverse_lazy("finance:cost-list")

    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            CostingService.delete_cost(self.object)
            messages.success(request, _("Cost entry moved to trash."))
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.get_success_url())


class CostEntryTrashListView(LoginRequiredMixin, ListView):
    model = CostEntry
    template_name = "finance/cost_trash_list.html"
    context_object_name = "costs"

    def get_queryset(self):
        return CostingService.get_deleted_costs()


class CostEntryRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            CostingService.restore_cost(pk)
            messages.success(request, _("Cost entry restored successfully."))
        except CostEntry.DoesNotExist:
            # Should not happen as PK comes from trash list, but good to handle
            messages.error(request, _("Cost entry not found."))
        except (ValidationError, ProtectedError) as e:
            messages.error(request, str(e))
        return HttpResponseRedirect(reverse_lazy("finance:cost-trash"))


class CostEntryPermanentDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, View):
    def post(self, request, pk):
        try:
            CostingService.hard_delete_cost(pk)
            messages.success(request, _("Cost entry permanently deleted."))
        except CostEntry.DoesNotExist:
            messages.error(request, _("Cost entry not found."))
        except (ValidationError, ProtectedError) as e:
            # Need to fetch object to render template if error, but here simplifying
            messages.error(request, str(e))

        return HttpResponseRedirect(reverse_lazy("finance:cost-trash"))
