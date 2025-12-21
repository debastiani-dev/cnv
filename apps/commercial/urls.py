from django.urls import path

from . import views

app_name = "commercial"

urlpatterns = [
    # Event Management
    path("", views.SalesEventListView.as_view(), name="event_list"),
    path("events/create/", views.SalesEventCreateView.as_view(), name="event_create"),
    path(
        "events/<uuid:pk>/update/",
        views.SalesEventUpdateView.as_view(),
        name="event_update",
    ),
    path(
        "events/<uuid:pk>/delete/",
        views.SalesEventDeleteView.as_view(),
        name="event_delete",
    ),
    path(
        "events/<uuid:pk>/toggle-active/",
        views.SalesEventToggleActiveView.as_view(),
        name="event_toggle_active",
    ),
    path(
        "events/<uuid:pk>/manage-lots/",
        views.ManageLotsView.as_view(),
        name="manage_lots",
    ),
    # Trash
    path("events/trash/", views.SalesEventTrashView.as_view(), name="event_trash"),
    path(
        "events/<uuid:pk>/restore/",
        views.SalesEventRestoreView.as_view(),
        name="event_restore",
    ),
    path(
        "events/<uuid:pk>/permanent-delete/",
        views.SalesEventHardDeleteView.as_view(),
        name="event_permanent_delete",
    ),
    # Lots
    path("lots/<uuid:pk>/print/", views.LotPrintView.as_view(), name="print_lot"),
    path("lots/<uuid:pk>/edit/", views.SalesLotUpdateView.as_view(), name="lot_update"),
    path(
        "lots/<uuid:pk>/delete/", views.SalesLotDeleteView.as_view(), name="lot_delete"
    ),
    path("lots/<uuid:pk>/close/", views.CloseLotView.as_view(), name="lot_close"),
    path(
        "events/<uuid:pk>/catalog/",
        views.EventCatalogView.as_view(),
        name="event_catalog",
    ),
]
