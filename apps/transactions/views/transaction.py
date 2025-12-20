from django.contrib import messages
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
from apps.transactions.forms import TransactionForm, TransactionItemFormSet
from apps.transactions.models.transaction import Transaction
from apps.transactions.services.transaction_service import TransactionService

TRANSACTION_LIST_URL = "transactions:list"


class TransactionListView(LoginRequiredMixin, StandardizedListMixin, ListView):
    model = Transaction
    template_name = "transactions/transaction_list.html"
    context_object_name = "transactions"
    ordering = ["-date"]
    paginate_by = 10

    def get_queryset(self):
        # We can implement a filter in service, or just filter here.
        # Let's simple filter here for now, or use service if complex.
        # Use Service for filtering
        queryset = TransactionService.get_all_transactions(
            search_query=self.request.GET.get("q"),
            partner_id=self.request.GET.get("partner"),
            transaction_type=self.request.GET.get("type"),
        )

        queryset = self.filter_by_date(queryset)

        return queryset.order_by("-date", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_partner"] = self.request.GET.get("partner", "")
        context["selected_type"] = self.request.GET.get("type", "")
        context["date_after"] = self.request.GET.get("date_after", "")
        context["date_before"] = self.request.GET.get("date_before", "")
        context["partners"] = Partner.objects.all()  # Show all partners
        context["type_choices"] = Transaction.TYPE_CHOICES
        return context


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy(TRANSACTION_LIST_URL)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("New Transaction")
        if self.request.POST:
            context["items"] = TransactionItemFormSet(self.request.POST)
        else:
            context["items"] = TransactionItemFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        if items.is_valid():
            try:
                with transaction.atomic():
                    self.object = form.save()
                    items.instance = self.object
                    items.save()
                    self.object.update_total()

                messages.success(self.request, _("Transaction created successfully."))
                return HttpResponseRedirect(self.get_success_url())
            except Exception as e:  # pylint: disable=broad-exception-caught
                form.add_error(None, str(e))
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy(TRANSACTION_LIST_URL)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Transaction")
        if self.request.POST:
            context["items"] = TransactionItemFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context["items"] = TransactionItemFormSet(instance=self.object)
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        if items.is_valid():
            with transaction.atomic():
                self.object = form.save()
                items.instance = self.object
                items.save()
                self.object.update_total()

            messages.success(self.request, _("Transaction updated successfully."))
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)


class TransactionDetailView(LoginRequiredMixin, DetailView):
    model = Transaction
    template_name = "transactions/transaction_detail.html"
    context_object_name = "transaction"


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = "transactions/transaction_confirm_delete.html"
    success_url = reverse_lazy(TRANSACTION_LIST_URL)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Transaction moved to trash."))
        return response


class TransactionTrashView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = "transactions/transaction_trash_list.html"
    context_object_name = "transactions"
    paginate_by = 10

    def get_queryset(self):
        return Transaction.all_objects.filter(is_deleted=True).order_by("-date")


class TransactionRestoreView(LoginRequiredMixin, UpdateView):
    model = Transaction
    fields = []
    template_name = "transactions/transaction_confirm_restore.html"
    success_url = reverse_lazy("transactions:trash")

    def get_queryset(self):
        return Transaction.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        self.object.restore()
        messages.success(self.request, _("Transaction restored successfully."))
        return super().form_valid(form)


class TransactionHardDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = "transactions/transaction_confirm_permanent_delete.html"
    success_url = reverse_lazy("transactions:trash")

    def get_queryset(self):
        return Transaction.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        self.object.delete(destroy=True)
        messages.success(self.request, _("Transaction permanently deleted."))
        return HttpResponseRedirect(self.success_url)
