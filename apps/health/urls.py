from django.urls import path

from apps.health.views import (
    MedicationCreateView,
    MedicationDeleteView,
    MedicationListView,
    MedicationUpdateView,
    SanitaryEventCreateView,
    SanitaryEventDeleteView,
    SanitaryEventDetailView,
    SanitaryEventHardDeleteView,
    SanitaryEventListView,
    SanitaryEventRestoreView,
    SanitaryEventTrashListView,
    SanitaryEventUpdateView,
)

app_name = "health"

urlpatterns = [
    path("events/", SanitaryEventListView.as_view(), name="event-list"),
    path("events/trash/", SanitaryEventTrashListView.as_view(), name="event-trash"),
    path("events/create/", SanitaryEventCreateView.as_view(), name="event-create"),
    path("events/<uuid:pk>/", SanitaryEventDetailView.as_view(), name="event-detail"),
    path(
        "events/<uuid:pk>/edit/", SanitaryEventUpdateView.as_view(), name="event-update"
    ),
    path(
        "events/<uuid:pk>/delete/",
        SanitaryEventDeleteView.as_view(),
        name="event-delete",
    ),
    path(
        "events/<uuid:pk>/restore/",
        SanitaryEventRestoreView.as_view(),
        name="event-restore",
    ),
    path(
        "events/<uuid:pk>/hard-delete/",
        SanitaryEventHardDeleteView.as_view(),
        name="event-hard-delete",
    ),
    # Medications
    path("medications/", MedicationListView.as_view(), name="medication-list"),
    path(
        "medications/create/", MedicationCreateView.as_view(), name="medication-create"
    ),
    path(
        "medications/<uuid:pk>/edit/",
        MedicationUpdateView.as_view(),
        name="medication-update",
    ),
    path(
        "medications/<uuid:pk>/delete/",
        MedicationDeleteView.as_view(),
        name="medication-delete",
    ),
]
