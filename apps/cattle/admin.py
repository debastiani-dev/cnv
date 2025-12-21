from django.contrib import admin

from apps.cattle.models import Cattle


@admin.register(Cattle)
class CattleAdmin(admin.ModelAdmin):
    list_display = [
        "tag",
        "name",
        "breed",
        "sex",
        "birth_date",
        "status",
        "pk",
    ]
    list_filter = ["status", "sex", "breed", "reproduction_status"]
    search_fields = ["tag", "name", "electronic_id"]
    readonly_fields = ["created_at", "modified_at", "uuid"]
