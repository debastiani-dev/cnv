from django.urls import path

from .api import AdgTrendApiView, StockingRateApiView
from .views import HomeView

app_name = "dashboard"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
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
]
