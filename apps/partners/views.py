from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
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
        return PartnerService.get_partners(search_query=q)


class PartnerTrashView(LoginRequiredMixin, ListView):
    model = Partner
    template_name = "partners/partner_trash_list.html"
    context_object_name = "favorites"  # Using same context name or "partners"? "partners" is better. keeping consistency with list view context usually.
    # Note: Using "partners" as context object name for consistency with template
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
        PartnerService.hard_delete_partner(self.object)
        from django.http import HttpResponseRedirect

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


class PartnerDetailView(LoginRequiredMixin, DetailView):
    model = Partner
    template_name = "partners/partner_detail.html"
    context_object_name = "partner"
