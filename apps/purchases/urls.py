from django.urls import path

from apps.purchases import views
from apps.purchases.views.api import ItemLookupView

app_name = "purchases"

urlpatterns = [
    path("", views.PurchaseListView.as_view(), name="list"),
    path("create/", views.PurchaseCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.PurchaseDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.PurchaseUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.PurchaseDeleteView.as_view(), name="delete"),
    path("trash/", views.PurchaseTrashView.as_view(), name="trash"),
    path("<uuid:pk>/restore/", views.PurchaseRestoreView.as_view(), name="restore"),
    path(
        "<uuid:pk>/permanent-delete/",
        views.PurchaseHardDeleteView.as_view(),
        name="permanent-delete",
    ),
    path("api/item-lookup/", ItemLookupView.as_view(), name="api-item-lookup"),
]
