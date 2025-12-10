from django.urls import path

from apps.reproduction.views.breeding import (
    BreedingCreateView,
    BreedingDeleteView,
    BreedingListView,
    BreedingPermanentDeleteView,
    BreedingRestoreView,
    BreedingTrashListView,
)
from apps.reproduction.views.calving import (
    CalvingCreateView,
    CalvingDeleteView,
    CalvingListView,
    CalvingPermanentDeleteView,
    CalvingRestoreView,
    CalvingTrashListView,
)
from apps.reproduction.views.diagnosis import (
    DiagnosisCreateView,
    DiagnosisDeleteView,
    DiagnosisListView,
    DiagnosisPermanentDeleteView,
    DiagnosisRestoreView,
    DiagnosisTrashListView,
)
from apps.reproduction.views.overview import ReproductionOverviewView
from apps.reproduction.views.season import (
    SeasonCreateView,
    SeasonDeleteView,
    SeasonListView,
    SeasonPermanentDeleteView,
    SeasonRestoreView,
    SeasonTrashListView,
    SeasonUpdateView,
)

app_name = "reproduction"

urlpatterns = [
    path("", ReproductionOverviewView.as_view(), name="overview"),
    path("breeding/", BreedingListView.as_view(), name="breeding_list"),
    path("breeding/add/", BreedingCreateView.as_view(), name="breeding_add"),
    path("breeding/trash/", BreedingTrashListView.as_view(), name="breeding_trash"),
    path(
        "breeding/<uuid:pk>/delete/",
        BreedingDeleteView.as_view(),
        name="breeding_delete",
    ),
    path(
        "breeding/<uuid:pk>/restore/",
        BreedingRestoreView.as_view(),
        name="breeding_restore",
    ),
    path(
        "breeding/<uuid:pk>/permanent-delete/",
        BreedingPermanentDeleteView.as_view(),
        name="breeding_permanent_delete",
    ),
    path("diagnosis/", DiagnosisListView.as_view(), name="diagnosis_list"),
    path("diagnosis/add/", DiagnosisCreateView.as_view(), name="diagnosis_add"),
    path("diagnosis/trash/", DiagnosisTrashListView.as_view(), name="diagnosis_trash"),
    path(
        "diagnosis/<uuid:pk>/restore/",
        DiagnosisRestoreView.as_view(),
        name="diagnosis_restore",
    ),
    path(
        "diagnosis/<uuid:pk>/delete/",
        DiagnosisDeleteView.as_view(),
        name="diagnosis_delete",
    ),
    path(
        "diagnosis/<uuid:pk>/permanent-delete/",
        DiagnosisPermanentDeleteView.as_view(),
        name="diagnosis_permanent_delete",
    ),
    path("calving/", CalvingListView.as_view(), name="calving_list"),
    path("calving/add/", CalvingCreateView.as_view(), name="calving_add"),
    path("calving/trash/", CalvingTrashListView.as_view(), name="calving_trash"),
    path(
        "calving/<uuid:pk>/restore/",
        CalvingRestoreView.as_view(),
        name="calving_restore",
    ),
    path(
        "calving/<uuid:pk>/delete/",
        CalvingDeleteView.as_view(),
        name="calving_delete",
    ),
    path(
        "calving/<uuid:pk>/permanent-delete/",
        CalvingPermanentDeleteView.as_view(),
        name="calving_permanent_delete",
    ),
    path("season/", SeasonListView.as_view(), name="season_list"),
    path("season/add/", SeasonCreateView.as_view(), name="season_add"),
    path("season/trash/", SeasonTrashListView.as_view(), name="season_trash"),
    path("season/<uuid:pk>/edit/", SeasonUpdateView.as_view(), name="season_edit"),
    path("season/<uuid:pk>/delete/", SeasonDeleteView.as_view(), name="season_delete"),
    path(
        "season/<uuid:pk>/restore/",
        SeasonRestoreView.as_view(),
        name="season_restore",
    ),
    path(
        "season/<uuid:pk>/permanent-delete/",
        SeasonPermanentDeleteView.as_view(),
        name="season_permanent_delete",
    ),
]
