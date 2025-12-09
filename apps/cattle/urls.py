from django.urls import path

from apps.cattle import views

app_name = "cattle"

urlpatterns = [
    path("", views.CattleListView.as_view(), name="list"),
    path("create/", views.CattleCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.CattleDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.CattleUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.CattleDeleteView.as_view(), name="delete"),
    path("trash/", views.CattleTrashListView.as_view(), name="trash"),
    path("<uuid:pk>/restore/", views.CattleRestoreView.as_view(), name="restore"),
    path(
        "<uuid:pk>/permanent-delete/",
        views.CattlePermanentDeleteView.as_view(),
        name="permanent-delete",
    ),
]
