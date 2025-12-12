from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView

from apps.base.views.list_mixins import StandardizedListMixin
from apps.cattle.models import Cattle
from apps.health.forms import SanitaryEventForm
from apps.health.models import SanitaryEvent
from apps.health.models.health import MedicationType
from apps.health.services import HealthService


class SanitaryEventCreateView(FormView):
    template_name = "health/sanitary_event_form.html"
    form_class = SanitaryEventForm
    success_url = reverse_lazy("cattle:list")  # Or health:event_list

    def post(self, request, *args, **kwargs):
        """
        Handles two types of POSTs:
        1. 'Initial': Incoming from Cattle List with just 'cattle_ids'.
        2. 'Save': Incoming from this form with data + 'cattle_ids'.
        """
        # Extract cattle IDs from either the List selection or the Hidden Fields
        cattle_ids = request.POST.getlist("cattle_ids")

        if not cattle_ids:
            messages.error(request, _("No cattle selected for this event."))
            return redirect("cattle:list")

        # Check if this is the actual Form Submission (checking for a known form field)
        # If 'action' is present, we are trying to save.
        if "action" in request.POST and request.POST["action"] == "save_event":
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form, cattle_ids)
            return self.form_invalid(form, cattle_ids)

        # Otherwise, this is the Initial request from Cattle List.
        # Render the empty form.
        return self.render_initial_form(cattle_ids)

    def render_initial_form(self, cattle_ids):
        """Helper to render the form with the selected cattle context"""
        form = self.get_form()
        context = self.get_context_data(form=form)

        # Fetch objects to show a summary (e.g. "Applying to 5 animals: Cow 101, Bull 202...")
        selected_cattle = Cattle.objects.filter(pk__in=cattle_ids)
        context["selected_cattle"] = selected_cattle
        context["cattle_ids"] = cattle_ids
        return render(self.request, self.template_name, context)

    # pylint: disable=arguments-differ
    def form_valid(self, form, cattle_ids):
        try:
            # Inject user who performed
            # Note: The form doesn't show 'performed_by' to keep it simple,
            # so we can auto-assign request.user or extract if added to form.
            # Ideally, event_data should have it.
            event_data = form.cleaned_data
            if not event_data.get("performed_by"):
                # If model allows it or logic requires, assign current user
                # But form.cleaned_data is a dict copy.
                pass

            # Note: HealthService.create_batch_event expects dict.
            # We might want to set performed_by to request.user if not in form.
            # But the user draft form has no performed_by field.
            # I will add it to the data.
            full_data = event_data.copy()
            full_data["performed_by"] = self.request.user

            HealthService.create_batch_event(
                event_data=full_data, cattle_uuids=cattle_ids
            )
            messages.success(self.request, _("Sanitary event created successfully."))
            return super().form_valid(form)
        except Exception as e:  # pylint: disable=broad-exception-caught
            # If service fails (e.g. data error), return to form with error
            messages.error(self.request, str(e))
            return self.form_invalid(form, cattle_ids)

    # pylint: disable=arguments-differ
    def form_invalid(self, form, cattle_ids):
        """
        If form fails (e.g. missing date), we MUST re-pass the cattle_ids
        so they aren't lost on the re-render.
        """
        context = self.get_context_data(form=form)
        context["selected_cattle"] = Cattle.objects.filter(pk__in=cattle_ids)
        context["cattle_ids"] = cattle_ids
        return render(self.request, self.template_name, context)


class SanitaryEventListView(LoginRequiredMixin, StandardizedListMixin, ListView):
    model = SanitaryEvent
    template_name = "health/event_list.html"
    context_object_name = "events"
    paginate_by = 10

    def get_queryset(self):
        queryset = (
            SanitaryEvent.objects.all()
            .select_related("medication", "performed_by")
            .annotate(animal_count=Count("targets"))
            .order_by("-date", "-created_at")
        )

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(notes__icontains=search_query)
            )

        medication_type = self.request.GET.get("medication_type")
        if (
            medication_type and medication_type != "None"
        ):  # Handle None explicitly if needed or just non-empty info
            # Filter by medication type join
            queryset = queryset.filter(medication__medication_type=medication_type)

        queryset = self.filter_by_date(queryset)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Search query and date params handled by mixin

        context["selected_medication_type"] = self.request.GET.get(
            "medication_type", ""
        )

        context["medication_type_choices"] = MedicationType.choices

        return context


class SanitaryEventDetailView(LoginRequiredMixin, DetailView):
    model = SanitaryEvent
    template_name = "health/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return super().get_queryset().select_related("medication", "performed_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add targets to context
        context["targets"] = (
            self.object.targets.all().select_related("animal").order_by("animal__tag")
        )
        return context


class SanitaryEventUpdateView(LoginRequiredMixin, UpdateView):
    model = SanitaryEvent
    form_class = SanitaryEventForm
    template_name = "health/event_form_update.html"

    def get_success_url(self):
        return reverse_lazy("health:event-detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)

        # 1. Handle Target Removal
        # Expecting a list of target IDs to remove in POST
        targets_to_remove = self.request.POST.getlist("remove_targets")
        if targets_to_remove:
            self.object.targets.filter(pk__in=targets_to_remove).delete()

        # 2. Recalculate Cost Allocation
        # If total_cost changed or targets were removed, we need to redistribute.
        if "total_cost" in form.changed_data or targets_to_remove:
            self._recalculate_costs()

        messages.success(self.request, _("Sanitary event updated successfully."))
        return response

    def _recalculate_costs(self):
        event = self.object
        targets = event.targets.all()
        count = targets.count()

        if count > 0:
            new_cost_per_head = event.total_cost / count
            targets.update(cost_per_head=new_cost_per_head)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["targets"] = (
            self.object.targets.all().select_related("animal").order_by("animal__tag")
        )
        return context


class SanitaryEventDeleteView(LoginRequiredMixin, DeleteView):
    model = SanitaryEvent
    template_name = "health/event_confirm_delete.html"
    success_url = reverse_lazy("health:event-list")

    # pylint: disable=broad-exception-caught
    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception as e:
            # Handle potential protected errors if any (though BaseModel soft deletes usually work fine)
            messages.error(self.request, str(e))
            return redirect("health:event-list")


class SanitaryEventTrashListView(LoginRequiredMixin, ListView):
    model = SanitaryEvent
    template_name = "health/event_trash_list.html"
    context_object_name = "events"
    paginate_by = 10

    def get_queryset(self):
        return HealthService.get_deleted_events()


class SanitaryEventRestoreView(LoginRequiredMixin, UpdateView):
    model = SanitaryEvent
    fields = []  # No fields needed for restore
    template_name = "health/event_confirm_restore.html"
    success_url = reverse_lazy("health:event-list")

    def get_queryset(self):
        # Need to be able to find deleted items to restore them
        return SanitaryEvent.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        HealthService.restore_event(self.object)
        messages.success(self.request, _("Event restored successfully."))
        return super().form_valid(form)


class SanitaryEventHardDeleteView(LoginRequiredMixin, DeleteView):
    model = SanitaryEvent
    template_name = "health/event_confirm_permanent_delete.html"
    success_url = reverse_lazy("health:event-list")

    def get_queryset(self):
        # Need to be able to find deleted items to hard delete them
        return SanitaryEvent.all_objects.filter(is_deleted=True)

    # pylint: disable=broad-exception-caught
    def form_valid(self, form):
        try:
            HealthService.hard_delete_event(self.object)
            messages.success(self.request, _("Event permanently deleted."))
        except Exception as e:
            # Handle potential protected errors
            messages.error(self.request, str(e))
            return render(
                self.request,
                self.template_name,
                {"object": self.object, "error": str(e)},
            )
        return redirect(self.success_url)
