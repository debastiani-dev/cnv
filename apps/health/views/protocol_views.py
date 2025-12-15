from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.health.forms import (
    HealthProtocolForm,
    ProtocolApplicationForm,
    ProtocolItemFormSet,
)
from apps.health.models import HealthProtocol
from apps.health.services import ProtocolService


class ProtocolListView(LoginRequiredMixin, ListView):
    model = HealthProtocol
    template_name = "health/protocol_list.html"
    context_object_name = "protocols"
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class ProtocolCreateView(LoginRequiredMixin, CreateView):
    model = HealthProtocol
    form_class = HealthProtocolForm
    template_name = "health/protocol_form.html"
    success_url = reverse_lazy("health:protocol-list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["items"] = ProtocolItemFormSet(self.request.POST)
        else:
            data["items"] = ProtocolItemFormSet()
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        with transaction.atomic():
            self.object = form.save()
            if items.is_valid():
                items.instance = self.object
                items.save()
        messages.success(self.request, _("Protocol created successfully."))
        return super().form_valid(form)


class ProtocolUpdateView(LoginRequiredMixin, UpdateView):
    model = HealthProtocol
    form_class = HealthProtocolForm
    template_name = "health/protocol_form.html"
    success_url = reverse_lazy("health:protocol-list")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["items"] = ProtocolItemFormSet(self.request.POST, instance=self.object)
        else:
            data["items"] = ProtocolItemFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        items = context["items"]
        with transaction.atomic():
            self.object = form.save()
            if items.is_valid():
                items.save()
        messages.success(self.request, _("Protocol updated successfully."))
        return super().form_valid(form)


class ProtocolDetailView(LoginRequiredMixin, DetailView):
    model = HealthProtocol
    template_name = "health/protocol_detail.html"
    context_object_name = "protocol"

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class ProtocolDeleteView(LoginRequiredMixin, DeleteView):
    model = HealthProtocol
    template_name = "health/protocol_confirm_delete.html"
    success_url = reverse_lazy("health:protocol-list")
    context_object_name = "protocol"

    def get_queryset(self):
        return HealthProtocol.all_objects.all()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.soft_delete()
            messages.success(request, _("Protocol moved to trash."))
        except ProtectedError:
            messages.error(
                request,
                _(
                    "Cannot delete this protocol because it is being used by other records."
                ),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            messages.error(
                request,
                _("An error occurred while deleting the protocol: {}").format(str(e)),
            )
        return redirect(self.success_url)


class ProtocolTrashListView(LoginRequiredMixin, ListView):
    model = HealthProtocol
    template_name = "health/protocol_trash_list.html"
    context_object_name = "protocols"
    ordering = ["-deleted_at"]

    def get_queryset(self):
        # Using AllObjectsManager or equivalent filter for is_deleted=True
        return HealthProtocol.all_objects.filter(is_deleted=True)


class ProtocolRestoreView(LoginRequiredMixin, View):
    def get(self, request, pk):
        protocol = get_object_or_404(HealthProtocol.all_objects, pk=pk)
        protocol.restore()
        messages.success(request, _("Protocol restored from trash."))
        return redirect("health:protocol-list")


class ProtocolHardDeleteView(LoginRequiredMixin, View):
    def get(self, request, pk):
        get_object_or_404(HealthProtocol.all_objects, pk=pk)
        return redirect(
            reverse("health:protocol-delete", kwargs={"pk": pk}) + "?hard=true"
        )

    def post(self, request, pk):
        protocol = get_object_or_404(HealthProtocol.all_objects, pk=pk)
        try:
            protocol.delete(destroy=True)
            messages.success(request, _("Protocol permanently deleted."))
        except ProtectedError:
            messages.error(
                request,
                _(
                    "Cannot permanently delete this protocol because it is referenced by other objects."
                ),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            messages.error(
                request,
                _("An error occurred while deleting the protocol: {}").format(str(e)),
            )
        return redirect("health:protocol-trash")


class ProtocolApplyView(LoginRequiredMixin, View):
    template_name = "health/protocol_apply.html"

    def post(self, request, *args, **kwargs):
        # Case 1: Submitting from Apply Form (Perform Phase)
        if "perform_application" in request.POST:
            form = ProtocolApplicationForm(request.POST, user=request.user)
            if form.is_valid():
                protocol = form.cleaned_data["protocol"]
                date = form.cleaned_data["date"]
                performed_by = form.cleaned_data["performed_by"]

                # cattle_ids are expected as a comma-separated string or list in POST
                cattle_ids = request.POST.get("cattle_ids_str", "").split(",")
                cattle_ids = [cid for cid in cattle_ids if cid]  # clean empty

                if not cattle_ids:
                    messages.error(request, _("No cattle selected."))
                    return redirect("cattle:list")

                try:
                    ProtocolService.apply_protocol(
                        protocol_id=protocol.pk,
                        target_cattle_ids=cattle_ids,
                        date=date,
                        performed_by=performed_by,
                    )
                    messages.success(
                        request,
                        _(
                            f"Protocol applied successfully to {len(cattle_ids)} animals."
                        ),
                    )
                    return redirect("cattle:list")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    messages.error(
                        request, _("Error applying protocol: {}").format(str(e))
                    )
                    # Ideally re-render form with error, but redirecting for simplicity now
                    return redirect("cattle:list")
            else:
                # Re-render with form errors
                cattle_ids_str = request.POST.get("cattle_ids_str", "")
                cattle_ids = cattle_ids_str.split(",") if cattle_ids_str else []
                return render(
                    request,
                    self.template_name,
                    {
                        "form": form,
                        "cattle_ids": cattle_ids,
                        "cattle_ids_str": cattle_ids_str,
                        "cattle_count": len(cattle_ids),
                    },
                )

        # Case 2: Submitting from Cattle List (Setup Phase)
        cattle_ids = request.POST.getlist("cattle_ids")
        if not cattle_ids:
            messages.warning(request, _("No cattle selected for protocol application."))
            return redirect("cattle:list")

        form = ProtocolApplicationForm(
            user=request.user, initial={"date": timezone.now().date()}
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "cattle_ids": cattle_ids,
                "cattle_ids_str": ",".join(cattle_ids),
                "cattle_count": len(cattle_ids),
            },
        )
