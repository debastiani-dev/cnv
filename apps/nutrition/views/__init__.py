from .diet_views import (
    DietCreateView,
    DietDeleteView,
    DietListView,
    DietPermanentDeleteView,
    DietRestoreView,
    DietTrashListView,
    DietUpdateView,
)
from .event_views import FeedingEventCreateView, FeedingEventListView
from .ingredient_views import (
    IngredientCreateView,
    IngredientDeleteView,
    IngredientListView,
    IngredientPermanentDeleteView,
    IngredientRestoreView,
    IngredientTrashListView,
    IngredientUpdateView,
)

__all__ = [
    "DietCreateView",
    "DietDeleteView",
    "DietListView",
    "DietPermanentDeleteView",
    "DietRestoreView",
    "DietTrashListView",
    "DietUpdateView",
    "IngredientCreateView",
    "IngredientDeleteView",
    "IngredientListView",
    "IngredientPermanentDeleteView",
    "IngredientRestoreView",
    "IngredientTrashListView",
    "IngredientUpdateView",
    "FeedingEventCreateView",
    "FeedingEventListView",
]
