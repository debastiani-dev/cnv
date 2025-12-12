from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import PartnerForm
from .models import Partner
from .services.partner_service import PartnerService

SUCCESS_URL = reverse_lazy("partners:list")


class PartnerListView(LoginRequiredMixin, ListView):
    model = Partner
    template_name = "partners/partner_list.html"
    context_object_name = "partners"
    paginate_by = 10

    def get_queryset(self):
        q = self.request.GET.get("q")
        role = self.request.GET.get("role")

        queryset = PartnerService.get_partners(search_query=q)

        if role == "customer":
            queryset = queryset.filter(is_customer=True)
        elif role == "supplier":
            queryset = queryset.filter(is_supplier=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_role"] = self.request.GET.get("role", "")
        context["role_choices"] = [
            ("customer", _("Customer")),
            ("supplier", _("Supplier")),
        ]

        return context


class PartnerTrashView(LoginRequiredMixin, ListView):
    model = Partner
    template_name = "partners/partner_trash_list.html"
    context_object_name = "partners"
    paginate_by = 10

    def get_queryset(self):
        return PartnerService.get_deleted_partners()


class PartnerRestoreView(LoginRequiredMixin, UpdateView):
    model = Partner
    fields = []  # No fields needed for restore
    template_name = "partners/partner_confirm_restore.html"
    success_url = SUCCESS_URL

    def get_queryset(self):
        # Need to be able to find deleted items to restore them
        return Partner.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        PartnerService.restore_partner(self.object)
        return super().form_valid(form)


class PartnerHardDeleteView(LoginRequiredMixin, DeleteView):
    model = Partner
    template_name = "partners/partner_confirm_permanent_delete.html"
    success_url = SUCCESS_URL

    def get_queryset(self):
        # Need to be able to find deleted items to hard delete them
        return Partner.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        try:
            PartnerService.hard_delete_partner(self.object)
        except (ValidationError, ProtectedError) as e:
            error_msg = e.message if hasattr(e, "message") else str(e)
            if isinstance(e, ProtectedError):
                error_msg = "Cannot delete this partner because it is referenced by other records."
            elif isinstance(e, ValidationError) and hasattr(e, "messages"):
                error_msg = e.messages[0]

            return render(
                self.request,
                self.template_name,
                {"object": self.object, "error": error_msg},
            )

        return HttpResponseRedirect(self.success_url)


class PartnerCreateView(LoginRequiredMixin, CreateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partners/partner_form.html"
    success_url = SUCCESS_URL
    extra_context = {"title": "Add Partner", "submit_text": "Save Partner"}


class PartnerUpdateView(LoginRequiredMixin, UpdateView):
    model = Partner
    form_class = PartnerForm
    template_name = "partners/partner_form.html"
    success_url = SUCCESS_URL
    extra_context = {"title": "Edit Partner", "submit_text": "Update Partner"}


class PartnerDeleteView(LoginRequiredMixin, DeleteView):
    model = Partner
    template_name = "partners/partner_confirm_delete.html"
    success_url = SUCCESS_URL

    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            PartnerService.delete_partner(self.object)
        except (ValidationError, ProtectedError) as e:
            error_msg = e.message if hasattr(e, "message") else str(e)
            if isinstance(e, ProtectedError):
                error_msg = "Cannot delete this partner because it is referenced by other records."
            elif isinstance(e, ValidationError) and hasattr(e, "messages"):
                error_msg = e.messages[0]

            return render(
                request, self.template_name, {"object": self.object, "error": error_msg}
            )
        return HttpResponseRedirect(self.success_url)


class PartnerDetailView(LoginRequiredMixin, DetailView):
    model = Partner
    template_name = "partners/partner_detail.html"
    context_object_name = "partner"
