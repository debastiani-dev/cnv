from django.contrib import messages
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
    View,
)

from apps.base.views.mixins import HandleProtectedErrorMixin
from apps.locations.forms import LocationForm
from apps.locations.models import Location, LocationStatus
from apps.locations.services import LocationService

LOCATION_LIST_URL = "locations:list"
LOCATION_NOT_FOUND_MSG = _("Location not found.")


class LocationListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = "locations/location_list.html"
    context_object_name = "locations"

    def get_queryset(self):
        # Prefetch cattle to optimize count queries in service
        return Location.objects.prefetch_related("cattle").order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate stats for each location
        location_stats = {}
        for location in context["locations"]:
            stats = LocationService.calculate_stocking_rate(location)

            # Determine Status Color/State for UI
            # Logic:
            # Red: Over capacity OR (Resting AND has animals)
            # Yellow: Resting (empty) OR Near capacity?
            # Green: Normal

            ui_status = "green"
            if location.status == LocationStatus.RESTING:
                if stats["head_count"] > 0:
                    ui_status = "red"  # Violation
                else:
                    ui_status = "yellow"
            elif (
                location.capacity_head and stats["head_count"] > location.capacity_head
            ):
                ui_status = "red"

            stats["ui_status"] = ui_status
            location_stats[location.pk] = stats

        context["location_stats"] = location_stats
        return context


class LocationDetailView(LoginRequiredMixin, DetailView):
    model = Location
    template_name = "locations/location_detail.html"
    context_object_name = "location"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Stats
        context["stats"] = LocationService.calculate_stocking_rate(self.object)

        # Inventory
        context["cattle_list"] = self.object.cattle.filter(
            is_deleted=False
        ).select_related("sire")

        # History (Log of In/Out)
        # Union of movements_in and movements_out or just list them?
        # Showing just recent movements involving this location
        movements = (
            (self.object.movements_in.all() | self.object.movements_out.all())
            .distinct()
            .order_by("-date")[:50]
        )
        context["movements"] = movements

        return context


class LocationCreateView(LoginRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = "locations/location_form.html"
    success_url = reverse_lazy(LOCATION_LIST_URL)


class LocationUpdateView(LoginRequiredMixin, UpdateView):
    model = Location
    form_class = LocationForm
    template_name = "locations/location_form.html"

    def get_success_url(self):
        return reverse_lazy("locations:detail", kwargs={"pk": self.object.pk})


class LocationDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView):
    model = Location
    template_name = "locations/location_confirm_delete.html"
    success_url = reverse_lazy(LOCATION_LIST_URL)

    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            # Standard delete calls model.delete() which does soft delete by default
            self.object.delete()
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.get_success_url())


class LocationTrashListView(LoginRequiredMixin, ListView):
    model = Location
    template_name = "locations/location_trash.html"
    context_object_name = "locations"

    def get_queryset(self):
        return LocationService.get_deleted_locations()


class LocationRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            LocationService.restore_location(pk)
            messages.success(request, _("Location restored successfully."))
        except Location.DoesNotExist:
            messages.error(request, LOCATION_NOT_FOUND_MSG)

        return HttpResponseRedirect(reverse_lazy(LOCATION_LIST_URL))

    def get(self, request, pk):
        try:
            location = Location.all_objects.get(pk=pk)
            return render(
                request,
                "locations/location_confirm_restore.html",
                {"location": location},
            )
        except Location.DoesNotExist:
            messages.error(request, LOCATION_NOT_FOUND_MSG)
            return HttpResponseRedirect(reverse_lazy(LOCATION_LIST_URL))


class LocationPermanentDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, View):
    def post(self, request, pk):
        try:
            LocationService.hard_delete_location(pk)
            messages.success(request, _("Location permanently deleted."))
        except Location.DoesNotExist:
            messages.error(request, LOCATION_NOT_FOUND_MSG)
        except (ValidationError, ProtectedError) as e:
            try:
                location = Location.all_objects.get(pk=pk)
                self.object = location
                return self.handle_delete_error(
                    request,
                    e,
                    template_name="locations/location_confirm_permanent_delete.html",
                    context_object_name="location",
                )
            except Location.DoesNotExist:
                pass

        return HttpResponseRedirect(reverse_lazy("locations:trash"))

    def get(self, request, pk):
        try:
            location = Location.all_objects.get(pk=pk)
            return render(
                request,
                "locations/location_confirm_permanent_delete.html",
                {"location": location},
            )
        except Location.DoesNotExist:
            messages.error(request, LOCATION_NOT_FOUND_MSG)
            return HttpResponseRedirect(reverse_lazy("locations:trash"))
