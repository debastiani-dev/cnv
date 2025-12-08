from django.urls import path

from apps.cattle.views import (
    CattleCreateView,
    CattleDeleteView,
    CattleDetailView,
    CattleListView,
    CattlePermanentDeleteView,
    CattleRestoreView,
    CattleTrashListView,
    CattleUpdateView,
)

# We don't define app_name here if we are including it into 'dashboard' namespace or similar.
# But good practice to keep it clean.
# However, the previous `apps/dashboard/urls.py` had `app_name = "dashboard"`.
# If we include this inside dashboard urls, the names will be `dashboard:cattle-list` etc.

urlpatterns = [
    path("", CattleListView.as_view(), name="cattle-list"),
    path("detail/<uuid:pk>/", CattleDetailView.as_view(), name="cattle-detail"),
    path("trash/", CattleTrashListView.as_view(), name="cattle-trash"),
    path("create/", CattleCreateView.as_view(), name="cattle-create"),
    path("update/<uuid:pk>/", CattleUpdateView.as_view(), name="cattle-update"),
    path("delete/<uuid:pk>/", CattleDeleteView.as_view(), name="cattle-delete"),
    path("restore/<uuid:pk>/", CattleRestoreView.as_view(), name="cattle-restore"),
    path(
        "delete-forever/<uuid:pk>/",
        CattlePermanentDeleteView.as_view(),
        name="cattle-permanent-delete",
    ),
]
