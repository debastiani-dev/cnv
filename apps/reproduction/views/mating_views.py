from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.base.views.mixins import HandleProtectedErrorMixin
from apps.reproduction.forms import MatingPlanForm
from apps.reproduction.models import MatingPlan
from apps.reproduction.services.mating_service import MatingPlanService

SUCCESS_URL_LIST = reverse_lazy("reproduction:matingplan_list")
ERROR_NOT_FOUND = _("Mating Plan not found.")


class MatingPlanListView(LoginRequiredMixin, ListView):
    model = MatingPlan
    template_name = "reproduction/matingplan_list.html"
    context_object_name = "plans"
    paginate_by = 10

    def get_queryset(self):
        return MatingPlanService.get_all_plans()


class MatingPlanDetailView(LoginRequiredMixin, DetailView):
    model = MatingPlan
    template_name = "reproduction/matingplan_detail.html"
    context_object_name = "plan"


class MatingPlanCreateView(LoginRequiredMixin, CreateView):
    model = MatingPlan
    form_class = MatingPlanForm
    template_name = "reproduction/matingplan_form.html"
    success_url = SUCCESS_URL_LIST

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Create Mating Plan")
        return context


class MatingPlanUpdateView(LoginRequiredMixin, UpdateView):
    model = MatingPlan
    form_class = MatingPlanForm
    template_name = "reproduction/matingplan_form.html"
    success_url = SUCCESS_URL_LIST

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Mating Plan")
        return context


class MatingPlanDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView):
    model = MatingPlan
    template_name = "reproduction/matingplan_confirm_delete.html"
    success_url = SUCCESS_URL_LIST

    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            MatingPlanService.delete_plan(self.object)
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.get_success_url())


class MatingPlanTrashListView(LoginRequiredMixin, ListView):
    model = MatingPlan
    template_name = "reproduction/matingplan_trash_list.html"
    context_object_name = "plans"

    def get_queryset(self):
        return MatingPlanService.get_deleted_plans()


class MatingPlanRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            MatingPlanService.restore_plan(pk)
            messages.success(request, _("Mating Plan restored successfully."))
        except Exception as e:  # pylint: disable=broad-exception-caught
            messages.error(request, str(e))

        return HttpResponseRedirect(SUCCESS_URL_LIST)

    def get(self, request, pk):
        try:
            plan = MatingPlan.all_objects.get(pk=pk)
            return render(
                request, "reproduction/matingplan_confirm_restore.html", {"plan": plan}
            )
        except MatingPlan.DoesNotExist:
            messages.error(request, ERROR_NOT_FOUND)
            return HttpResponseRedirect(SUCCESS_URL_LIST)


class MatingPlanHardDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, View):
    def post(self, request, pk):
        try:
            MatingPlanService.hard_delete_plan(pk)
            messages.success(request, _("Mating Plan permanently deleted."))
        except MatingPlan.DoesNotExist:
            messages.error(request, ERROR_NOT_FOUND)
        except (ValidationError, ProtectedError) as e:
            try:
                plan = MatingPlan.all_objects.get(pk=pk)
                self.object = plan
                return self.handle_delete_error(
                    request,
                    e,
                    template_name="reproduction/matingplan_confirm_permanent_delete.html",
                    context_object_name="plan",
                )
            except MatingPlan.DoesNotExist:
                pass  # Should stick to message error above

        return HttpResponseRedirect(reverse_lazy("reproduction:matingplan_trash"))

    def get(self, request, pk):
        try:
            plan = MatingPlan.all_objects.get(pk=pk)
            return render(
                request,
                "reproduction/matingplan_confirm_permanent_delete.html",
                {"plan": plan},
            )
        except MatingPlan.DoesNotExist:
            messages.error(request, ERROR_NOT_FOUND)
            return HttpResponseRedirect(reverse_lazy("reproduction:matingplan_trash"))
