from django.urls import path

from apps.genetics import views

app_name = "genetics"

urlpatterns = [
    # Storage Tanks
    path("tanks/", views.StorageTankListView.as_view(), name="tank-list"),
    path("tanks/<uuid:pk>/", views.StorageTankDetailView.as_view(), name="tank-detail"),
    path("tanks/new/", views.StorageTankCreateView.as_view(), name="tank-create"),
    path(
        "tanks/<uuid:pk>/edit/",
        views.StorageTankUpdateView.as_view(),
        name="tank-update",
    ),
    path(
        "tanks/<uuid:pk>/delete/",
        views.StorageTankDeleteView.as_view(),
        name="tank-delete",
    ),
    path("tanks/trash/", views.StorageTankTrashView.as_view(), name="tank-trash"),
    path(
        "tanks/<uuid:pk>/restore/",
        views.StorageTankRestoreView.as_view(),
        name="tank-restore",
    ),
    path(
        "tanks/<uuid:pk>/permanent-delete/",
        views.StorageTankPermanentDeleteView.as_view(),
        name="tank-permanent-delete",
    ),
    # Semen Batches
    path("semen/", views.SemenBatchListView.as_view(), name="semen-list"),
    path("semen/<uuid:pk>/", views.SemenBatchDetailView.as_view(), name="semen-detail"),
    path("semen/new/", views.SemenBatchCreateView.as_view(), name="semen-create"),
    path(
        "semen/<uuid:pk>/edit/",
        views.SemenBatchUpdateView.as_view(),
        name="semen-update",
    ),
    path(
        "semen/<uuid:pk>/delete/",
        views.SemenBatchDeleteView.as_view(),
        name="semen-delete",
    ),
    path("semen/trash/", views.SemenBatchTrashView.as_view(), name="semen-trash"),
    path(
        "semen/<uuid:pk>/restore/",
        views.SemenBatchRestoreView.as_view(),
        name="semen-restore",
    ),
    path(
        "semen/<uuid:pk>/permanent-delete/",
        views.SemenBatchPermanentDeleteView.as_view(),
        name="semen-permanent-delete",
    ),
    path(
        "semen/<uuid:pk>/adjust-stock/",
        views.SemenBatchStockAdjustmentView.as_view(),
        name="semen-adjust-stock",
    ),
    # Embryo Batches
    path("embryos/", views.EmbryoBatchListView.as_view(), name="embryo-list"),
    path(
        "embryos/<uuid:pk>/",
        views.EmbryoBatchDetailView.as_view(),
        name="embryo-detail",
    ),
    path("embryos/new/", views.EmbryoBatchCreateView.as_view(), name="embryo-create"),
    path(
        "embryos/<uuid:pk>/edit/",
        views.EmbryoBatchUpdateView.as_view(),
        name="embryo-update",
    ),
    path(
        "embryos/<uuid:pk>/delete/",
        views.EmbryoBatchDeleteView.as_view(),
        name="embryo-delete",
    ),
    path("embryos/trash/", views.EmbryoBatchTrashView.as_view(), name="embryo-trash"),
    path(
        "embryos/<uuid:pk>/restore/",
        views.EmbryoBatchRestoreView.as_view(),
        name="embryo-restore",
    ),
    path(
        "embryos/<uuid:pk>/permanent-delete/",
        views.EmbryoBatchPermanentDeleteView.as_view(),
        name="embryo-permanent-delete",
    ),
    path(
        "embryos/<uuid:pk>/adjust-stock/",
        views.EmbryoBatchStockAdjustmentView.as_view(),
        name="embryo-adjust-stock",
    ),
]
