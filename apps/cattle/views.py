from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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

from apps.cattle.forms import CattleForm
from apps.cattle.models import Cattle
from apps.cattle.services.cattle_service import CattleService


class CattleDetailView(LoginRequiredMixin, DetailView):
    model = Cattle
    template_name = "cattle/cattle_detail.html"
    context_object_name = "cattle"


class CattleListView(LoginRequiredMixin, ListView):
    model = Cattle
    template_name = "cattle/cattle_list.html"
    context_object_name = "cattle_list"
    paginate_by = 10

    def get_queryset(self):
        search_query = self.request.GET.get("q")
        breed = self.request.GET.get("breed")
        status = self.request.GET.get("status")
        return CattleService.get_all_cattle(
            search_query=search_query, breed=breed, status=status
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_breed"] = self.request.GET.get("breed", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["breed_choices"] = Cattle.BREED_CHOICES
        context["status_choices"] = Cattle.STATUS_CHOICES
        return context


class CattleCreateView(LoginRequiredMixin, CreateView):
    model = Cattle
    form_class = CattleForm
    template_name = "cattle/cattle_form.html"
    success_url = reverse_lazy("dashboard:cattle-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Add Cattle")
        return context

    def form_valid(self, form):
        self.object = CattleService.create_cattle(form.cleaned_data)
        return HttpResponseRedirect(self.get_success_url())


class CattleUpdateView(LoginRequiredMixin, UpdateView):
    model = Cattle
    form_class = CattleForm
    template_name = "cattle/cattle_form.html"
    success_url = reverse_lazy("dashboard:cattle-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Cattle")
        return context

    def form_valid(self, form):
        CattleService.update_cattle(self.object, form.cleaned_data)
        return HttpResponseRedirect(self.get_success_url())


class CattleDeleteView(LoginRequiredMixin, DeleteView):
    model = Cattle
    template_name = "cattle/cattle_confirm_delete.html"
    success_url = reverse_lazy("dashboard:cattle-list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        CattleService.delete_cattle(self.object)
        return HttpResponseRedirect(self.get_success_url())


class CattleTrashListView(LoginRequiredMixin, ListView):
    model = Cattle
    template_name = "cattle/cattle_trash_list.html"
    context_object_name = "cattle_list"

    def get_queryset(self):
        return CattleService.get_deleted_cattle()


class CattleRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            CattleService.restore_cattle(pk)
            messages.success(request, _("Cattle restored successfully."))
        except ValueError as e:
            messages.error(request, str(e))
        except Cattle.DoesNotExist:
            messages.error(request, _("Cattle not found."))

        return HttpResponseRedirect(reverse_lazy("dashboard:cattle-list"))

    def get(self, request, pk):
        try:
            cattle = Cattle.all_objects.get(pk=pk)
            return render(
                request, "cattle/cattle_confirm_restore.html", {"cattle": cattle}
            )
        except Cattle.DoesNotExist:
            messages.error(request, _("Cattle not found."))
            return HttpResponseRedirect(reverse_lazy("dashboard:cattle-list"))


class CattlePermanentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            CattleService.hard_delete_cattle(pk)
            messages.success(request, _("Cattle permanently deleted."))
        except Cattle.DoesNotExist:
            messages.error(request, _("Cattle not found."))

        return HttpResponseRedirect(reverse_lazy("dashboard:cattle-trash"))

    def get(self, request, pk):
        try:
            cattle = Cattle.all_objects.get(pk=pk)
            return render(
                request,
                "cattle/cattle_confirm_permanent_delete.html",
                {"cattle": cattle},
            )
        except Cattle.DoesNotExist:
            messages.error(request, _("Cattle not found."))
            return HttpResponseRedirect(reverse_lazy("dashboard:cattle-trash"))
