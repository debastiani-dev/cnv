from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import ListView

from apps.base.views.list_mixins import StandardizedListMixin
from apps.notifications.models import Notification


class NotificationListView(StandardizedListMixin, LoginRequiredMixin, ListView):
    model = Notification
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)

        # Search
        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(message__icontains=search_query)
            )

        # Filter by Category
        category = self.request.GET.get("category")
        if category:
            queryset = queryset.filter(category=category)

        # Filter by Status (Read/Unread)
        status = self.request.GET.get("status")
        if status == "read":
            queryset = queryset.filter(is_read=True)
        elif status == "unread":
            queryset = queryset.filter(is_read=False)

        # Date filtering (Mixin)
        queryset = self.filter_by_date(queryset, field_name="created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_choices"] = Notification.Category.choices
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_status"] = self.request.GET.get("status", "")
        return context
