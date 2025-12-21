from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.dashboard.services import DashboardService


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # New Dashboard Architecture: The Decision Engine
        context["alerts"] = DashboardService.get_critical_alerts(user=self.request.user)
        context["finance"] = DashboardService.get_financial_kpis()
        context["commercial"] = DashboardService.get_commercial_pulse()
        context["herd"] = DashboardService.get_herd_status()
        context["operations"] = DashboardService.get_operational_stats(
            user=self.request.user
        )

        return context
