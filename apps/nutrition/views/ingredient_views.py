from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from apps.base.views.list_mixins import StandardizedListMixin
from apps.base.views.mixins import HandleProtectedErrorMixin, SafeDeleteMixin
from apps.nutrition.forms import FeedIngredientForm
from apps.nutrition.models import FeedIngredient
from apps.nutrition.services import IngredientService

INGREDIENT_LIST_URL = "nutrition:ingredient-list"
INGREDIENT_NOT_FOUND_MSG = _("Ingredient not found.")


class IngredientListView(LoginRequiredMixin, StandardizedListMixin, ListView):
    model = FeedIngredient
    template_name = "nutrition/ingredient_list.html"
    context_object_name = "ingredients"
    paginate_by = 20
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        return queryset


class IngredientCreateView(LoginRequiredMixin, CreateView):
    model = FeedIngredient
    form_class = FeedIngredientForm
    template_name = "nutrition/ingredient_form.html"
    success_url = reverse_lazy(INGREDIENT_LIST_URL)


class IngredientUpdateView(LoginRequiredMixin, UpdateView):
    model = FeedIngredient
    form_class = FeedIngredientForm
    template_name = "nutrition/ingredient_form.html"
    success_url = reverse_lazy(INGREDIENT_LIST_URL)


class IngredientDeleteView(LoginRequiredMixin, SafeDeleteMixin, DeleteView):
    model = FeedIngredient
    template_name = "nutrition/ingredient_confirm_delete.html"
    success_url = reverse_lazy(INGREDIENT_LIST_URL)


class IngredientTrashListView(LoginRequiredMixin, ListView):
    model = FeedIngredient
    template_name = "nutrition/ingredient_trash.html"
    context_object_name = "ingredients"

    def get_queryset(self):
        return IngredientService.get_deleted_ingredients()


class IngredientRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            IngredientService.restore_ingredient(pk)
            messages.success(request, _("Ingredient restored successfully."))
        except FeedIngredient.DoesNotExist:
            messages.error(request, INGREDIENT_NOT_FOUND_MSG)

        return HttpResponseRedirect(reverse_lazy(INGREDIENT_LIST_URL))

    def get(self, request, pk):
        try:
            ingredient = FeedIngredient.all_objects.get(pk=pk)
            return render(
                request,
                "nutrition/ingredient_confirm_restore.html",
                {"ingredient": ingredient},
            )
        except FeedIngredient.DoesNotExist:
            messages.error(request, INGREDIENT_NOT_FOUND_MSG)
            return HttpResponseRedirect(reverse_lazy(INGREDIENT_LIST_URL))


class IngredientPermanentDeleteView(
    LoginRequiredMixin, HandleProtectedErrorMixin, View
):
    def post(self, request, pk):
        try:
            IngredientService.hard_delete_ingredient(pk)
            messages.success(request, _("Ingredient permanently deleted."))
        except FeedIngredient.DoesNotExist:
            messages.error(request, INGREDIENT_NOT_FOUND_MSG)
        except (ValidationError, ProtectedError) as e:
            try:
                ingredient = FeedIngredient.all_objects.get(pk=pk)
                self.object = ingredient
                return self.handle_delete_error(
                    request,
                    e,
                    template_name="nutrition/ingredient_confirm_permanent_delete.html",
                    context_object_name="ingredient",
                )
            except FeedIngredient.DoesNotExist:
                pass

        return HttpResponseRedirect(reverse_lazy("nutrition:ingredient-trash"))

    def get(self, request, pk):
        try:
            ingredient = FeedIngredient.all_objects.get(pk=pk)
            return render(
                request,
                "nutrition/ingredient_confirm_permanent_delete.html",
                {"ingredient": ingredient},
            )
        except FeedIngredient.DoesNotExist:
            messages.error(request, INGREDIENT_NOT_FOUND_MSG)
            return HttpResponseRedirect(reverse_lazy("nutrition:ingredient-trash"))
