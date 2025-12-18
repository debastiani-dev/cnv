from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from apps.locations.models import Location, LocationType
from apps.locations.services.allocation import AllocationService
from apps.reproduction.models import MatingPlan


class MatingPlanAllocationView(LoginRequiredMixin, DetailView):
    model = MatingPlan
    template_name = "reproduction/mating_allocation.html"
    context_object_name = "plan"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plan = self.object

        # Calculate Total AU
        sire_au = AllocationService.get_au(plan.sire)
        cows_au = sum(AllocationService.get_au(cow) for cow in plan.cows.all())
        total_au = sire_au + cows_au
        context["total_au"] = total_au

        # Analyze all Pastures
        all_pastures = Location.objects.filter(
            type=LocationType.PASTURE, is_active=True
        ).order_by("name")
        paddock_options = []

        # Prepare mock list of animals for validation
        # We need a list of cattle objects to pass to validate_move
        animals_to_move = [plan.sire] + list(plan.cows.all())

        for paddock in all_pastures:
            result = AllocationService.validate_move(paddock, animals_to_move)

            status = "valid"
            label_class = "bg-green-100 text-green-800"
            icon = "🟢"

            if not result["valid"]:
                status = "error"
                label_class = "bg-red-100 text-red-800"
                icon = "🔴"
            elif result["warnings"]:
                status = "warning"
                label_class = "bg-yellow-100 text-yellow-800"
                icon = "🟡"

            paddock_options.append(
                {
                    "location": paddock,
                    "status": status,
                    "label_class": label_class,
                    "icon": icon,
                    "errors": result["errors"],
                    "warnings": result["warnings"],
                }
            )

        context["paddock_options"] = paddock_options
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        plan = self.object
        paddock_id = request.POST.get("paddock_id")

        if not paddock_id:
            # "Decide Later" case
            # Stay APPROVED_WAITING
            messages.info(
                request, _("Allocation deferred. Plan saved as 'Waiting for Location'.")
            )
            return HttpResponseRedirect(reverse("reproduction:matingplan_list"))

        try:
            paddock = Location.objects.get(pk=paddock_id)

            # Create Movement Task (or execute move directly for this prototype)
            # Implementation Plan says "Offer to Create a Movement Task" or "Execute".
            # For "Move Wizard" completion, let's update Plan to ACTIVE and move animals.
            # In a real app we'd spawn a celery task or MoveRequest object.
            # Here we just Sim-Move.

            with transaction.atomic():
                # Update Plan
                plan.status = MatingPlan.Status.ACTIVE
                plan.save()

                # Move Animals
                # 1. Sire
                plan.sire.location = paddock
                plan.sire.save()

                # 2. Cows
                plan.cows.update(location=paddock)

            messages.success(
                request,
                _("Plan Activated! Animals moved to %(paddock)s.")
                % {"paddock": paddock.name},
            )
            return HttpResponseRedirect(reverse("reproduction:matingplan_list"))

        except Location.DoesNotExist:
            messages.error(request, _("Invalid Paddock selected."))
            return HttpResponseRedirect(reverse("reproduction:matingplan_list"))
