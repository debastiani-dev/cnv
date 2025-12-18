import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.cattle.models import Cattle
from apps.reproduction.models import MatingPlan, ReproductiveSeason
from apps.reproduction.services.genetics import InbreedingService


class MatingSimulatorView(LoginRequiredMixin, TemplateView):
    template_name = "reproduction/mating_simulator.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Load available Bulls (Sires)
        context["sires"] = Cattle.objects.filter(
            sex=Cattle.SEX_MALE, status=Cattle.STATUS_AVAILABLE
        ).order_by("tag")

        # Load available Cows (Females, Open/Lactating preferred)
        # For simulator, we might want to list ALL active females,
        # but focused on those ready for breeding.
        context["cows"] = (
            Cattle.objects.filter(
                sex=Cattle.SEX_FEMALE,
                status=Cattle.STATUS_AVAILABLE,
                reproduction_status__in=[
                    Cattle.REP_STATUS_OPEN,
                    Cattle.REP_STATUS_LACTATING,
                ],
            )
            .select_related("sire", "dam")
            .order_by("tag")
        )

        # In a real app with 10k cows, we wouldn't dump them all here.
        # But for this MVP/Prototype, we load them for the JS drag-drop/selector.

        return context


class MatingAnalysisView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        sire_id = data.get("sire_id")
        cow_ids = data.get("cow_ids", [])

        if not sire_id or not cow_ids:
            return JsonResponse({"error": "Missing sire or cows"}, status=400)

        try:
            sire = Cattle.objects.get(pk=sire_id)
        except Cattle.DoesNotExist:
            return JsonResponse({"error": "Sire not found"}, status=404)

        cows = Cattle.objects.filter(pk__in=cow_ids)
        results = []

        for cow in cows:
            coefficient, risk_level, details = InbreedingService.calculate_coefficient(
                sire, cow
            )
            results.append(
                {
                    "cow_id": cow.pk,
                    "cow_tag": cow.tag,
                    "risk_level": risk_level,
                    "coefficient": coefficient,
                    "details": details,
                }
            )

        return JsonResponse({"results": results})


class MatingPlanBulkCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        sire_id = data.get("sire_id")
        cow_ids = data.get("cow_ids", [])

        if not sire_id or not cow_ids:
            return JsonResponse({"error": "Missing sire or cows"}, status=400)

        try:
            sire = Cattle.objects.get(pk=sire_id)
        except Cattle.DoesNotExist:
            return JsonResponse({"error": "Sire not found"}, status=404)

        # Find active season or create/get default
        # In a real app we'd ask user to select season. Here we try to find one.
        season = ReproductiveSeason.objects.filter(
            start_date__lte=timezone.now(), end_date__gte=timezone.now()
        ).first()
        if not season:
            # Fallback for prototype: just get last one or create dummy if none
            season = ReproductiveSeason.objects.last()

        if not season:
            return JsonResponse(
                {
                    "error": (
                        "No active Reproductive Season found. Please create one first."
                    )
                },
                status=400,
            )

        # Create Plan
        # Default status: APPROVED_WAITING (Proposed solution in task.md)
        # Or DRAFT? Implementation Plan said "Approve All Safe Matches -> Creates MatingPlan".
        # Let's create as APPROVED_WAITING directly so it goes to "Allocation" status.

        plan = MatingPlan.objects.create(
            season=season,
            sire=sire,
            status=MatingPlan.Status.APPROVED_WAITING,
            notes=f"Auto-generated plan from Simulator on {timezone.now().date()}",
        )

        # Add Cows
        cows = Cattle.objects.filter(pk__in=cow_ids)
        plan.cows.set(cows)

        return JsonResponse({"status": "success", "plan_id": plan.pk})
