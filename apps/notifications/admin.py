from django.contrib import admin

from .models.notification import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "category", "is_read", "created_at")
    list_filter = ("category", "is_read", "created_at")
    search_fields = ("title", "message", "recipient__username", "recipient__email")
    readonly_fields = ("created_at", "modified_at")
