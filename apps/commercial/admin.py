from django.contrib import admin

from .models import SalesEvent, SalesLot


class SalesLotInline(admin.TabularInline):
    model = SalesLot
    extra = 1
    autocomplete_fields = ["animals"]


@admin.register(SalesEvent)
class SalesEventAdmin(admin.ModelAdmin):
    list_display = ["name", "date", "sales_type", "is_active"]
    list_filter = ["sales_type", "date", "is_active"]
    search_fields = ["name"]
    inlines = [SalesLotInline]


@admin.register(SalesLot)
class SalesLotAdmin(admin.ModelAdmin):
    list_display = [
        "lot_number",
        "event",
        "status",
        "animals_count",
        "reserve_price",
    ]
    list_filter = ["event", "status"]
    search_fields = ["lot_number", "event__name"]
    filter_horizontal = ["animals"]

    @admin.display(description="Animals")
    def animals_count(self, obj):
        return obj.animals.count()
