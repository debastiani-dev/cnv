from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import CreateView, ListView

from apps.reproduction.models import BreedingEvent
from apps.reproduction.services.reproduction_service import ReproductionService


class BreedingListView(ListView):
    model = BreedingEvent
    template_name = "reproduction/breeding_event_list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        return BreedingEvent.objects.select_related("dam", "sire", "batch").order_by(
            "-date"
        )


class BreedingCreateView(CreateView):
    model = BreedingEvent
    fields = ["dam", "date", "breeding_method", "sire", "sire_name", "batch"]
    template_name = "reproduction/breeding_event_form.html"
    success_url = reverse_lazy("reproduction:breeding_list")

    def form_valid(self, form):
        try:
            ReproductionService.record_breeding(
                dam=form.cleaned_data["dam"],
                date=form.cleaned_data["date"],
                method=form.cleaned_data["breeding_method"],
                sire=form.cleaned_data["sire"],
                sire_name=form.cleaned_data["sire_name"],
                batch=form.cleaned_data["batch"],
            )
            messages.success(self.request, _("Breeding recorded successfully."))
            return redirect(self.success_url)
        except (ValueError, ValidationError) as e:
            form.add_error(None, str(e))
            return self.form_invalid(form)


class BreedingTrashListView(LoginRequiredMixin, ListView):
    model = BreedingEvent
    template_name = "reproduction/breeding_event_trash_list.html"
    context_object_name = "events"

    def get_queryset(self):
        return ReproductionService.get_deleted_breeding_events()


class BreedingRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            ReproductionService.restore_breeding_event(pk)
            messages.success(request, _("Breeding event restored successfully."))
        except ValueError as e:
            messages.error(request, str(e))
        except BreedingEvent.DoesNotExist:
            messages.error(request, _("Breeding event not found."))

        return redirect("reproduction:breeding_list")

    def get(self, request, pk):
        try:
            event = BreedingEvent.all_objects.get(pk=pk)
            return render(
                request,
                "reproduction/breeding_event_confirm_restore.html",
                {"event": event},
            )
        except BreedingEvent.DoesNotExist:
            messages.error(request, _("Breeding event not found."))
            return redirect("reproduction:breeding_list")


class BreedingPermanentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            ReproductionService.hard_delete_breeding_event(pk)
            messages.success(request, _("Breeding event permanently deleted."))
        except BreedingEvent.DoesNotExist:
            messages.error(request, _("Breeding event not found."))

        return redirect("reproduction:breeding_trash")

    def get(self, request, pk):
        try:
            event = BreedingEvent.all_objects.get(pk=pk)
            return render(
                request,
                "reproduction/breeding_event_confirm_permanent_delete.html",
                {"event": event},
            )
        except BreedingEvent.DoesNotExist:
            messages.error(request, _("Breeding event not found."))
            return redirect("reproduction:breeding_trash")


class BreedingDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            event = BreedingEvent.objects.get(pk=pk)
            event.delete()
            messages.success(request, _("Breeding event deleted."))
        except BreedingEvent.DoesNotExist:
            messages.error(request, _("Breeding event not found."))

        return redirect("reproduction:breeding_list")

    def get(self, request, pk):
        try:
            event = BreedingEvent.objects.get(pk=pk)
            return render(
                request,
                "reproduction/breeding_event_confirm_delete.html",
                {"object": event},
            )
        except BreedingEvent.DoesNotExist:
            messages.error(request, _("Breeding event not found."))
            return redirect("reproduction:breeding_list")
