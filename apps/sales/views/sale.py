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

from apps.base.views.list_mixins import StandardizedListMixin
from apps.partners.models.partner import Partner
from apps.sales.forms import SaleForm, SaleItemFormSet
from apps.sales.models import Sale
from apps.sales.services.sale_service import SaleService

SALE_LIST_URL = "sales:list"


class SaleListView(LoginRequiredMixin, StandardizedListMixin, ListView):
    model = Sale
    template_name = "sales/sale_list.html"
    context_object_name = "sales"
    ordering = ["-date"]
    paginate_by = 10

    def get_queryset(self):
        search_query = self.request.GET.get("q")
        partner_id = self.request.GET.get("partner")

        queryset = SaleService.get_all_sales(
            search_query=search_query, partner_id=partner_id
        )

        queryset = self.filter_by_date(queryset)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["selected_partner"] = self.request.GET.get("partner", "")
        # Date params and search query are handled by mixin, but mixin adds search_query
        # We need to ensure mixin's get_context_data is called or we call it and add our extras.
        # StandardizedListMixin.get_context_data calls super().

        context["partners"] = Partner.objects.filter(is_customer=True)

        return context


class SaleCreateView(LoginRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = "sales/sale_form.html"
    success_url = reverse_lazy(SALE_LIST_URL)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("New Sale")
        if self.request.POST:
            context["items"] = SaleItemFormSet(self.request.POST)
        else:
            context["items"] = SaleItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        if items.is_valid():
            try:
                SaleService.create_sale_from_forms(form, items)
                return super().form_valid(form)  # Redirects to success_url
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Handle error
                form.add_error(None, str(e))
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)


class SaleUpdateView(LoginRequiredMixin, UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = "sales/sale_form.html"
    success_url = reverse_lazy(SALE_LIST_URL)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Sale")
        if self.request.POST:
            context["items"] = SaleItemFormSet(self.request.POST, instance=self.object)
        else:
            context["items"] = SaleItemFormSet(instance=self.object)
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
                SaleService.update_sale_totals(self.object)

            return super().form_valid(form)
        return self.form_invalid(form)


class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = "sales/sale_detail.html"
    context_object_name = "sale"


class SaleDeleteView(LoginRequiredMixin, DeleteView):
    model = Sale
    template_name = "sales/sale_confirm_delete.html"
    success_url = reverse_lazy(SALE_LIST_URL)


class SaleTrashView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = "sales/sale_trash_list.html"
    context_object_name = "sales"
    paginate_by = 10

    def get_queryset(self):
        return SaleService.get_deleted_sales()


class SaleRestoreView(LoginRequiredMixin, UpdateView):
    model = Sale
    fields = []
    template_name = "sales/sale_confirm_restore.html"
    success_url = reverse_lazy("sales:trash")

    def get_queryset(self):
        return Sale.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        SaleService.restore_sale(self.object)
        return super().form_valid(form)


class SaleHardDeleteView(LoginRequiredMixin, DeleteView):
    model = Sale
    template_name = "sales/sale_confirm_permanent_delete.html"
    success_url = reverse_lazy("sales:trash")

    def get_queryset(self):
        return Sale.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        SaleService.hard_delete_sale(self.object)

        return HttpResponseRedirect(self.success_url)
