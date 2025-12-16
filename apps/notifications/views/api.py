from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from apps.notifications.models import Notification


class NotificationListApiView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        """
        Get unread notifications and count.
        Query params: ?all=true to get all notifications (paginated)
        """
        show_all = request.GET.get("all") == "true"

        qs = Notification.objects.filter(recipient=request.user)
        unread_count = qs.filter(is_read=False).count()

        if not show_all:
            # By default just show unread or recent 5?
            # Implementation plan said "List unread" for /api/notifications/
            # And /api/notifications/all/ for all.
            # I'll implement this view to handle both or just unread + recent 5.
            # Let's stick to returning recent unread for the dropdown.
            qs = qs.filter(is_read=False)

        # Limit to 5 for the dropdown use case usually, but let's return last 10
        notifications = qs.order_by("-created_at")[:10]

        data = {
            "unread_count": unread_count,
            "notifications": [
                {
                    "id": n.pk,
                    "title": n.title,
                    "message": n.message,
                    "category": n.category,
                    "link": n.link,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat(),
                    "params": {},  # Placeholder for any extra data if needed
                }
                for n in notifications
            ],
        }
        return JsonResponse(data)


class NotificationMarkReadApiView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        """
        Mark a single notification as read.
        """
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({"status": "success"})


class NotificationMarkAllReadApiView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        """
        Mark all notifications as read for the user.
        """
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True
        )
        return JsonResponse({"status": "success"})
