from django.urls import path

from . import views

app_name = "weight"

urlpatterns = [
    path("", views.WeighingSessionListView.as_view(), name="session-list"),
    path("trash/", views.WeighingSessionTrashListView.as_view(), name="session-trash"),
    path("add/", views.WeighingSessionCreateView.as_view(), name="session-create"),
    path(
        "<uuid:pk>/", views.WeighingSessionDetailView.as_view(), name="session-detail"
    ),
    path(
        "<uuid:pk>/edit/",
        views.WeighingSessionUpdateView.as_view(),
        name="session-update",
    ),
    path(
        "<uuid:pk>/delete/",
        views.WeighingSessionDeleteView.as_view(),
        name="session-delete",
    ),
    path(
        "<uuid:pk>/restore/",
        views.WeighingSessionRestoreView.as_view(),
        name="session-restore",
    ),
    path(
        "<uuid:pk>/permanent-delete/",
        views.WeighingSessionHardDeleteView.as_view(),
        name="session-hard-delete",
    ),
    path(
        "<uuid:pk>/batch-entry/", views.BatchWeighingView.as_view(), name="batch-entry"
    ),
    # Record URLs
    path(
        "record/<uuid:pk>/edit/",
        views.WeightRecordUpdateView.as_view(),
        name="record-update",
    ),
    path(
        "record/<uuid:pk>/delete/",
        views.WeightRecordDeleteView.as_view(),
        name="record-delete",
    ),
]
