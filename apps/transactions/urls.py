from django.urls import path

from apps.transactions import views
from apps.transactions.views.api import ItemLookupView

app_name = "transactions"

urlpatterns = [
    path("", views.TransactionListView.as_view(), name="list"),
    path("create/", views.TransactionCreateView.as_view(), name="create"),
    path("<uuid:pk>/", views.TransactionDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.TransactionUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", views.TransactionDeleteView.as_view(), name="delete"),
    path("trash/", views.TransactionTrashView.as_view(), name="trash"),
    path("<uuid:pk>/restore/", views.TransactionRestoreView.as_view(), name="restore"),
    path(
        "<uuid:pk>/permanent-delete/",
        views.TransactionHardDeleteView.as_view(),
        name="permanent-delete",
    ),
    path("api/item-lookup/", ItemLookupView.as_view(), name="api-item-lookup"),
]
