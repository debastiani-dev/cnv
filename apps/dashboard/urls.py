from django.urls import include, path

from .views import HomeView

app_name = "dashboard"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("cattle/", include("apps.cattle.urls")),
]
