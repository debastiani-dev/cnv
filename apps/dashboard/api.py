from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View

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
