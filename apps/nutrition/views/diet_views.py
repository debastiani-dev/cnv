from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from apps.base.views.list_mixins import StandardizedListMixin
from apps.base.views.mixins import HandleProtectedErrorMixin, SafeDeleteMixin
from apps.nutrition.forms import DietForm, DietItemFormSet
from apps.nutrition.models import Diet
from apps.nutrition.services import DietService

DIET_LIST_URL = "nutrition:diet-list"
DIET_NOT_FOUND_MSG = _("Diet not found.")


class DietListView(StandardizedListMixin, ListView):
    model = Diet
    template_name = "nutrition/diet_list.html"
    context_object_name = "diets"
    paginate_by = 20

    def get_queryset(self):
        queryset = Diet.objects.prefetch_related("items__ingredient").order_by("name")

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        return queryset


class DietCreateView(CreateView):
    model = Diet
    form_class = DietForm
    template_name = "nutrition/diet_form.html"
    success_url = reverse_lazy(DIET_LIST_URL)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["items"] = DietItemFormSet(self.request.POST)
        else:
            data["items"] = DietItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        with transaction.atomic():
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
            else:
                return self.form_invalid(form)
        return super().form_valid(form)


class DietUpdateView(UpdateView):
    model = Diet
    form_class = DietForm
    template_name = "nutrition/diet_form.html"
    success_url = reverse_lazy(DIET_LIST_URL)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["items"] = DietItemFormSet(self.request.POST, instance=self.object)
        else:
            data["items"] = DietItemFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        with transaction.atomic():
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
            else:
                return self.form_invalid(form)
        return super().form_valid(form)


class DietDeleteView(LoginRequiredMixin, SafeDeleteMixin, DeleteView):
    model = Diet
    template_name = "nutrition/diet_confirm_delete.html"
    success_url = reverse_lazy(DIET_LIST_URL)


class DietTrashListView(LoginRequiredMixin, ListView):
    model = Diet
    template_name = "nutrition/diet_trash.html"
    context_object_name = "diets"

    def get_queryset(self):
        return DietService.get_deleted_diets()


class DietRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            DietService.restore_diet(pk)
            messages.success(request, _("Diet restored successfully."))
        except Diet.DoesNotExist:
            messages.error(request, DIET_NOT_FOUND_MSG)

        return HttpResponseRedirect(reverse_lazy(DIET_LIST_URL))

    def get(self, request, pk):
        try:
            diet = Diet.all_objects.get(pk=pk)
            return render(
                request,
                "nutrition/diet_confirm_restore.html",
                {"diet": diet},
            )
        except Diet.DoesNotExist:
            messages.error(request, DIET_NOT_FOUND_MSG)
            return HttpResponseRedirect(reverse_lazy(DIET_LIST_URL))


class DietPermanentDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, View):
    def post(self, request, pk):
        try:
            DietService.hard_delete_diet(pk)
            messages.success(request, _("Diet permanently deleted."))
        except Diet.DoesNotExist:
            messages.error(request, DIET_NOT_FOUND_MSG)
        except (ValidationError, ProtectedError) as e:
            try:
                diet = Diet.all_objects.get(pk=pk)
                self.object = diet
                return self.handle_delete_error(
                    request,
                    e,
                    template_name="nutrition/diet_confirm_permanent_delete.html",
                    context_object_name="diet",
                )
            except Diet.DoesNotExist:
                pass

        return HttpResponseRedirect(reverse_lazy("nutrition:diet-trash"))

    def get(self, request, pk):
        try:
            diet = Diet.all_objects.get(pk=pk)
            return render(
                request,
                "nutrition/diet_confirm_permanent_delete.html",
                {"diet": diet},
            )
        except Diet.DoesNotExist:
            messages.error(request, DIET_NOT_FOUND_MSG)
            return HttpResponseRedirect(reverse_lazy("nutrition:diet-trash"))
