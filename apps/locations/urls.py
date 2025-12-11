from django.urls import path

from . import views

app_name = "locations"

urlpatterns = [
    path("", views.LocationListView.as_view(), name="list"),
    path("trash/", views.LocationTrashListView.as_view(), name="trash"),
    path("create/", views.LocationCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.LocationDetailView.as_view(), name="detail"),
    path("<uuid:pk>/update/", views.LocationUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.LocationDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/restore/", views.LocationRestoreView.as_view(), name="restore"),
    path(
        "<uuid:pk>/hard-delete/",
        views.LocationPermanentDeleteView.as_view(),
        name="hard-delete",
    ),
    path("move/", views.MovementCreateView.as_view(), name="move"),
]
