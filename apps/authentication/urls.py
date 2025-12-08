from django.urls import path

from .views import LoginView, LogoutView
from .views.user_crud import (
    UserCreateView,
    UserDeletePermanentView,
    UserDeleteView,
    UserDetailView,
    UserListView,
    UserRestoreView,
    UserTrashView,
    UserUpdateView,
)

app_name = "authentication"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # User CRUD
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("users/create/", UserCreateView.as_view(), name="user-create"),
    path("users/<uuid:pk>/edit/", UserUpdateView.as_view(), name="user-update"),
    path("users/<uuid:pk>/delete/", UserDeleteView.as_view(), name="user-delete"),
    # Trash Bin
    path("users/trash/", UserTrashView.as_view(), name="user-trash"),
    path("users/<uuid:pk>/restore/", UserRestoreView.as_view(), name="user-restore"),
    path(
        "users/<uuid:pk>/permanent-delete/",
        UserDeletePermanentView.as_view(),
        name="user-permanent-delete",
    ),
]
