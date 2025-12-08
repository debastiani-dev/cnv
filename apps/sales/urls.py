from django.urls import path

from apps.sales import views
from apps.sales.views.api import ItemLookupView

app_name = "sales"

urlpatterns = [
    path("", views.SaleListView.as_view(), name="list"),
    path("create/", views.SaleCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.SaleDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.SaleUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.SaleDeleteView.as_view(), name="delete"),
    path("trash/", views.SaleTrashView.as_view(), name="trash"),
    path("<uuid:pk>/restore/", views.SaleRestoreView.as_view(), name="restore"),
    path(
        "<uuid:pk>/permanent-delete/",
        views.SaleHardDeleteView.as_view(),
        name="permanent-delete",
    ),
    path("api/item-lookup/", ItemLookupView.as_view(), name="api-item-lookup"),
]
