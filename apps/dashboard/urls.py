from django.urls import path

from .api import StockingRateApiView
from .views import HomeView

app_name = "dashboard"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path(
        "api/stocking-rate/",
        StockingRateApiView.as_view(),
        name="stocking-rate-api",
    ),
]
