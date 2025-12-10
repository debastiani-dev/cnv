from .event_views import (
    SanitaryEventCreateView,
    SanitaryEventDeleteView,
    SanitaryEventDetailView,
    SanitaryEventHardDeleteView,
    SanitaryEventListView,
    SanitaryEventRestoreView,
    SanitaryEventTrashListView,
    SanitaryEventUpdateView,
)
from .medication_views import (
    MedicationCreateView,
    MedicationDeleteView,
    MedicationListView,
    MedicationPermanentDeleteView,
    MedicationRestoreView,
    MedicationTrashListView,
    MedicationUpdateView,
)

__all__ = [
    "SanitaryEventCreateView",
    "SanitaryEventDeleteView",
    "SanitaryEventDetailView",
    "SanitaryEventHardDeleteView",
    "SanitaryEventListView",
    "SanitaryEventRestoreView",
    "SanitaryEventTrashListView",
    "SanitaryEventUpdateView",
    "MedicationCreateView",
    "MedicationDeleteView",
    "MedicationListView",
    "MedicationPermanentDeleteView",
    "MedicationRestoreView",
    "MedicationTrashListView",
    "MedicationUpdateView",
]
