from django.urls import path
from apps.cattle.views import (
    CattleListView, CattleCreateView, CattleUpdateView, CattleDeleteView,
    CattleTrashListView, CattleRestoreView, CattlePermanentDeleteView
)

# We don't define app_name here if we are including it into 'dashboard' namespace or similar.
# But good practice to keep it clean.
# However, the previous `apps/dashboard/urls.py` had `app_name = "dashboard"`.
# If we include this inside dashboard urls, the names will be `dashboard:cattle-list` etc.

urlpatterns = [
    path("", CattleListView.as_view(), name="cattle-list"),
    path("trash/", CattleTrashListView.as_view(), name="cattle-trash"),
    path("create/", CattleCreateView.as_view(), name="cattle-create"),
    path("update/<int:pk>/", CattleUpdateView.as_view(), name="cattle-update"),
    path("delete/<int:pk>/", CattleDeleteView.as_view(), name="cattle-delete"),
    path("restore/<int:pk>/", CattleRestoreView.as_view(), name="cattle-restore"),
    path("delete-forever/<int:pk>/", CattlePermanentDeleteView.as_view(), name="cattle-permanent-delete"),
]
