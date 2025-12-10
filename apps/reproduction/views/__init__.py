from .breeding import BreedingCreateView, BreedingListView
from .calving import CalvingCreateView, CalvingListView
from .diagnosis import DiagnosisCreateView, DiagnosisListView
from .overview import ReproductionOverviewView

__all__ = [
    "ReproductionOverviewView",
    "BreedingListView",
    "BreedingCreateView",
    "DiagnosisListView",
    "DiagnosisCreateView",
    "CalvingListView",
    "CalvingCreateView",
]
