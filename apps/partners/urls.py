from django.urls import path

from . import views

app_name = "partners"

urlpatterns = [
    path("", views.PartnerListView.as_view(), name="list"),
    path("trash/", views.PartnerTrashView.as_view(), name="trash"),
    path("create/", views.PartnerCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.PartnerDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.PartnerUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.PartnerDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/restore/", views.PartnerRestoreView.as_view(), name="restore"),
    path(
        "<uuid:pk>/hard-delete/",
        views.PartnerHardDeleteView.as_view(),
        name="hard-delete",
    ),
]
