from django.urls import path

from .api import (
    AdgTrendApiView,
    ChartFinancialTrendApiView,
    ChartGeneticProgressApiView,
    StockingRateApiView,
)
from .views import HomeView

app_name = "dashboard"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    # Old APIs (kept for backward compatibility if needed, or remove if unused)
    path(
        "api/stocking-rate/",
        StockingRateApiView.as_view(),
        name="stocking-rate-api",
    ),
    path(
        "api/adg-trend/",
        AdgTrendApiView.as_view(),
        name="adg-trend-api",
    ),
    # New Dashboard Overhaul APIs
    path(
        "api/chart/financial-trend/",
        ChartFinancialTrendApiView.as_view(),
        name="chart-financial-trend",
    ),
    path(
        "api/chart/genetic-progress/",
        ChartGeneticProgressApiView.as_view(),
        name="chart-genetic-progress",
    ),
]
