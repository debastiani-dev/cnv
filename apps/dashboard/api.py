from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

from apps.dashboard.services import DashboardService
from apps.locations.services.analytics import get_stocking_rate_metrics
from apps.weight.services.analytics import get_global_adg_metrics


class StockingRateApiView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        data = get_stocking_rate_metrics()
        return JsonResponse(data)


class AdgTrendApiView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        data = get_global_adg_metrics()
        return JsonResponse(data)


class ChartFinancialTrendApiView(LoginRequiredMixin, View):
    """
    Returns monthly aggregation of Transactions for the chart.
    """

    def get(self, request, *args, **kwargs):
        data = DashboardService.get_financial_trend()
        return JsonResponse(data, safe=False)


class ChartGeneticProgressApiView(LoginRequiredMixin, View):
    """
    Returns Avg Weaning Weight grouped by Birth Year.
    """

    def get(self, request, *args, **kwargs):
        data = DashboardService.get_genetic_progress()
        return JsonResponse(data, safe=False)
