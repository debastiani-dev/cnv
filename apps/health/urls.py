from django.urls import path

from apps.health.views import (
    MedicationCreateView,
    MedicationDeleteView,
    MedicationListView,
    MedicationPermanentDeleteView,
    MedicationRestoreView,
    MedicationTrashListView,
    MedicationUpdateView,
    ProtocolApplyView,
    ProtocolCreateView,
    ProtocolDeleteView,
    ProtocolDetailView,
    ProtocolHardDeleteView,
    ProtocolListView,
    ProtocolRestoreView,
    ProtocolTrashListView,
    ProtocolUpdateView,
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
        "medications/trash/",
        MedicationTrashListView.as_view(),
        name="medication-trash",
    ),
    path(
        "medications/<uuid:pk>/",
        MedicationUpdateView.as_view(),
        name="medication-detail",
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
    path(
        "medications/<uuid:pk>/restore/",
        MedicationRestoreView.as_view(),
        name="medication-restore",
    ),
    path(
        "medications/<uuid:pk>/permanent-delete/",
        MedicationPermanentDeleteView.as_view(),
        name="medication-permanent-delete",
    ),
    # Protocols
    path("protocols/", ProtocolListView.as_view(), name="protocol-list"),
    path("protocols/create/", ProtocolCreateView.as_view(), name="protocol-create"),
    path("protocols/<uuid:pk>/", ProtocolDetailView.as_view(), name="protocol-detail"),
    path(
        "protocols/<uuid:pk>/edit/",
        ProtocolUpdateView.as_view(),
        name="protocol-update",
    ),
    path(
        "protocols/<uuid:pk>/delete/",
        ProtocolDeleteView.as_view(),
        name="protocol-delete",
    ),
    path("protocols/trash/", ProtocolTrashListView.as_view(), name="protocol-trash"),
    path(
        "protocols/<uuid:pk>/restore/",
        ProtocolRestoreView.as_view(),
        name="protocol-restore",
    ),
    path(
        "protocols/<uuid:pk>/hard-delete/",
        ProtocolHardDeleteView.as_view(),
        name="protocol-hard-delete",
    ),
    path(
        "protocols/apply/",
        ProtocolApplyView.as_view(),
        name="protocol-apply",
    ),
]
