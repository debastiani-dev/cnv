# pylint: disable=duplicate-code
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.purchases.forms import PurchaseForm, PurchaseItemFormSet
from apps.purchases.models import Purchase
from apps.purchases.services.purchase_service import PurchaseService


class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    template_name = "purchases/purchase_list.html"
    context_object_name = "purchases"
    ordering = ["-date"]
    paginate_by = 10


class PurchaseCreateView(LoginRequiredMixin, CreateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "purchases/purchase_form.html"
    success_url = reverse_lazy("purchases:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("New Purchase")
        if self.request.POST:
            context["items"] = PurchaseItemFormSet(self.request.POST)
        else:
            context["items"] = PurchaseItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        if items.is_valid():
            try:
                PurchaseService.create_purchase_from_forms(form, items)
                return super().form_valid(form)  # Redirects to success_url
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Handle error
                form.add_error(None, str(e))
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)


class PurchaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "purchases/purchase_form.html"
    success_url = reverse_lazy("purchases:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Purchase")
        if self.request.POST:
            context["items"] = PurchaseItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["items"] = PurchaseItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        if items.is_valid():
            # We can reuse the logic, form.save() updates instance, forms set updates items.
            # Service might duplicate creation logic if not careful.
            # For update, we can just save them standardly, but total calculation needs to happen.
            # Let's use service logic adapted or just manual save + service total update.
            with transaction.atomic():
                self.object = form.save()
                items.save()  # Handles add/edit

                # Handle deletions explicitly if items.save() doesn't
                # (it usually does if commit=True).
                # inlineformset_factory saves deleted objects too.

                # Update totals
                PurchaseService.update_purchase_totals(self.object)

            return super().form_valid(form)
        return self.form_invalid(form)


class PurchaseDetailView(LoginRequiredMixin, DetailView):
    model = Purchase
    template_name = "purchases/purchase_detail.html"
    context_object_name = "purchase"


class PurchaseDeleteView(LoginRequiredMixin, DeleteView):
    model = Purchase
    template_name = "purchases/purchase_confirm_delete.html"
    success_url = reverse_lazy("purchases:list")


class PurchaseTrashView(LoginRequiredMixin, ListView):
    model = Purchase
    template_name = "purchases/purchase_trash_list.html"
    context_object_name = "purchases"
    paginate_by = 10

    def get_queryset(self):
        return PurchaseService.get_deleted_purchases()


class PurchaseRestoreView(LoginRequiredMixin, UpdateView):
    model = Purchase
    fields = []
    template_name = "purchases/purchase_confirm_restore.html"
    success_url = reverse_lazy("purchases:trash")

    def get_queryset(self):
        return Purchase.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        PurchaseService.restore_purchase(self.object)
        return super().form_valid(form)


class PurchaseHardDeleteView(LoginRequiredMixin, DeleteView):
    model = Purchase
    template_name = "purchases/purchase_confirm_permanent_delete.html"
    success_url = reverse_lazy("purchases:trash")

    def get_queryset(self):
        return Purchase.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        PurchaseService.hard_delete_purchase(self.object)

        return HttpResponseRedirect(self.success_url)
