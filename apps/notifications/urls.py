from django.urls import path

from .views import (
    NotificationListApiView,
    NotificationListView,
    NotificationMarkAllReadApiView,
    NotificationMarkReadApiView,
)

app_name = "notifications"

urlpatterns = [
    path("list/", NotificationListView.as_view(), name="list"),
    path("api/list/", NotificationListApiView.as_view(), name="api-list"),
    path(
        "api/<uuid:pk>/mark-read/",
        NotificationMarkReadApiView.as_view(),
        name="api-mark-read",
    ),
    path(
        "api/mark-all-read/",
        NotificationMarkAllReadApiView.as_view(),
        name="api-mark-all-read",
    ),
]
