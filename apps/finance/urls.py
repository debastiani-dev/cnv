from django.urls import path

from apps.finance.views import batch_views, cost_views

app_name = "finance"

urlpatterns = [
    # Active Costs
    path("costs/", cost_views.CostEntryListView.as_view(), name="cost-list"),
    path("costs/add/", cost_views.CostEntryCreateView.as_view(), name="cost-create"),
    path(
        "costs/batch-add/",
        batch_views.CostBatchCreateView.as_view(),
        name="cost-batch-create",
    ),
    path(
        "costs/<uuid:pk>/edit/",
        cost_views.CostEntryUpdateView.as_view(),
        name="cost-update",
    ),
    path(
        "costs/<uuid:pk>/delete/",
        cost_views.CostEntryDeleteView.as_view(),
        name="cost-delete",
    ),
    # Trash Bin
    path(
        "costs/trash/", cost_views.CostEntryTrashListView.as_view(), name="cost-trash"
    ),
    path(
        "costs/<uuid:pk>/restore/",
        cost_views.CostEntryRestoreView.as_view(),
        name="cost-restore",
    ),
    path(
        "costs/<uuid:pk>/hard-delete/",
        cost_views.CostEntryPermanentDeleteView.as_view(),
        name="cost-permanent-delete",
    ),
]
