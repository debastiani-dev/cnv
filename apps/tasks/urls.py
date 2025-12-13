from django.urls import path

from apps.base.views.api import ItemLookupView
from apps.tasks.views import (
    TaskCalendarView,
    TaskCreateView,
    TaskDeleteView,
    TaskDetailView,
    TaskEventsView,
    TaskListView,
    TaskPermanentDeleteView,
    TaskRestoreView,
    TaskTrashListView,
    TaskUpdateView,
)

app_name = "tasks"

urlpatterns = [
    path("calendar/", TaskCalendarView.as_view(), name="calendar"),
    path("list/", TaskListView.as_view(), name="list"),
    path("create/", TaskCreateView.as_view(), name="create"),
    path("<uuid:pk>/", TaskDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", TaskUpdateView.as_view(), name="update"),
    path("<uuid:pk>/delete/", TaskDeleteView.as_view(), name="delete"),
    path("trash/", TaskTrashListView.as_view(), name="trash"),
    path("<uuid:pk>/restore/", TaskRestoreView.as_view(), name="restore"),
    path(
        "<uuid:pk>/permanent-delete/",
        TaskPermanentDeleteView.as_view(),
        name="permanent-delete",
    ),
    path("api/events/", TaskEventsView.as_view(), name="api-events"),
    path("api/item-lookup/", ItemLookupView.as_view(), name="api-item-lookup"),
]
