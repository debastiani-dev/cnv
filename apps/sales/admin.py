from django.contrib import admin
from apps.sales.models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1
    autocomplete_fields = [] # Cannot autocomplete generic FK easily without config

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("date", "type", "partner", "total_amount")
    list_filter = ("type", "date")
    search_fields = ("partner__name",)
    inlines = [SaleItemInline]
