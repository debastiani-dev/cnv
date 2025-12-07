from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from apps.cattle.services.cattle_service import CattleService
from apps.cattle.forms import CattleForm
from apps.cattle.models import Cattle

class CattleListView(LoginRequiredMixin, ListView):
    model = Cattle
    template_name = "cattle/cattle_list.html"
    context_object_name = "cattle_list"
    paginate_by = 10

    def get_queryset(self):
        return CattleService.get_all_cattle()

class CattleCreateView(LoginRequiredMixin, CreateView):
    model = Cattle
    form_class = CattleForm
    template_name = "cattle/cattle_form.html"
    success_url = reverse_lazy("dashboard:cattle-list")

    def form_valid(self, form):
        self.object = CattleService.create_cattle(form.cleaned_data)
        return HttpResponseRedirect(self.get_success_url())

class CattleUpdateView(LoginRequiredMixin, UpdateView):
    model = Cattle
    form_class = CattleForm
    template_name = "cattle/cattle_form.html"
    success_url = reverse_lazy("dashboard:cattle-list")

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
            messages.success(request, "Cattle restored successfully.")
        except ValueError as e:
            messages.error(request, str(e))
        except Cattle.DoesNotExist:
            messages.error(request, "Cattle not found.")
            
        return HttpResponseRedirect(reverse_lazy("dashboard:cattle-list"))
    
    def get(self, request, pk):
        try:
            cattle = Cattle.all_objects.get(pk=pk)
            return render(request, "cattle/cattle_confirm_restore.html", {"cattle": cattle})
        except Cattle.DoesNotExist:
            messages.error(request, "Cattle not found.")
            return HttpResponseRedirect(reverse_lazy("dashboard:cattle-list"))

class CattlePermanentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            CattleService.hard_delete_cattle(pk)
            messages.success(request, "Cattle permanently deleted.")
        except Cattle.DoesNotExist:
            messages.error(request, "Cattle not found.")
            
        return HttpResponseRedirect(reverse_lazy("dashboard:cattle-trash"))

    def get(self, request, pk):
        try:
            cattle = Cattle.all_objects.get(pk=pk)
            return render(request, "cattle/cattle_confirm_permanent_delete.html", {"cattle": cattle})
        except Cattle.DoesNotExist:
            messages.error(request, "Cattle not found.")
            return HttpResponseRedirect(reverse_lazy("dashboard:cattle-trash"))
