from django.contrib import admin

from apps.purchases.models import Purchase, PurchaseItem


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    autocomplete_fields = []  # Cannot autocomplete generic FK easily without config


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("date", "type", "partner", "total_amount")
    list_filter = ("type", "date")
    search_fields = ("partner__name",)
    inlines = [PurchaseItemInline]
