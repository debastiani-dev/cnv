from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.utils import timezone
from django.views.generic import TemplateView

from apps.cattle.models.cattle import Cattle
from apps.reproduction.models import BreedingEvent, Calving, ReproductiveSeason


class ReproductionOverviewView(LoginRequiredMixin, TemplateView):
    template_name = "reproduction/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate Stats
        context["total_females"] = Cattle.objects.filter(
            sex=Cattle.SEX_FEMALE, status=Cattle.STATUS_AVAILABLE
        ).count()
        context["open_cows"] = Cattle.objects.filter(
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
        ).count()
        context["bred_cows"] = Cattle.objects.filter(
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_BRED,
        ).count()
        context["pregnant_cows"] = Cattle.objects.filter(
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
        ).count()

        # Recent Activity
        context["recent_breedings"] = BreedingEvent.objects.order_by("-date")[:5]
        context["recent_calvings"] = Calving.objects.order_by("-date")[:5]

        # Active Season (Calculated by Date)
        today = timezone.now().date()
        context["active_season"] = (
            ReproductiveSeason.objects.filter(start_date__lte=today)
            .filter(models.Q(end_date__gte=today) | models.Q(end_date__isnull=True))
            .order_by("-start_date")
            .first()
        )

        return context
