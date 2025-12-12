from django.urls import path

from apps.nutrition import views

app_name = "nutrition"

urlpatterns = [
    # Diet Management
    path("diets/", views.DietListView.as_view(), name="diet-list"),
    path("diets/create/", views.DietCreateView.as_view(), name="diet-create"),
    path("diets/trash/", views.DietTrashListView.as_view(), name="diet-trash"),
    path("diets/<uuid:pk>/update/", views.DietUpdateView.as_view(), name="diet-update"),
    path("diets/<uuid:pk>/delete/", views.DietDeleteView.as_view(), name="diet-delete"),
    path(
        "diets/<uuid:pk>/restore/", views.DietRestoreView.as_view(), name="diet-restore"
    ),
    path(
        "diets/<uuid:pk>/hard-delete/",
        views.DietPermanentDeleteView.as_view(),
        name="diet-hard-delete",
    ),
    # Ingredient Management
    path("ingredients/", views.IngredientListView.as_view(), name="ingredient-list"),
    path(
        "ingredients/create/",
        views.IngredientCreateView.as_view(),
        name="ingredient-create",
    ),
    path(
        "ingredients/trash/",
        views.IngredientTrashListView.as_view(),
        name="ingredient-trash",
    ),
    path(
        "ingredients/<uuid:pk>/update/",
        views.IngredientUpdateView.as_view(),
        name="ingredient-update",
    ),
    path(
        "ingredients/<uuid:pk>/delete/",
        views.IngredientDeleteView.as_view(),
        name="ingredient-delete",
    ),
    path(
        "ingredients/<uuid:pk>/restore/",
        views.IngredientRestoreView.as_view(),
        name="ingredient-restore",
    ),
    path(
        "ingredients/<uuid:pk>/hard-delete/",
        views.IngredientPermanentDeleteView.as_view(),
        name="ingredient-hard-delete",
    ),
    # Feeding Events
    path("events/", views.FeedingEventListView.as_view(), name="event-list"),
    path("events/create/", views.FeedingEventCreateView.as_view(), name="event-create"),
]
