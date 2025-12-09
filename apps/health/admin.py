from django.contrib import admin

from apps.health.models.health import Medication, SanitaryEvent, SanitaryEventTarget


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "medication_type",
        "unit",
        "withdrawal_days_meat",
        "withdrawal_days_milk",
    )
    search_fields = ("name", "active_ingredient")
    list_filter = ("medication_type", "unit")


class SanitaryEventTargetInline(admin.TabularInline):
    model = SanitaryEventTarget
    extra = 1


@admin.register(SanitaryEvent)
class SanitaryEventAdmin(admin.ModelAdmin):
    list_display = ("date", "title", "medication", "total_cost", "created_at")
    inlines = [SanitaryEventTargetInline]
    search_fields = ("title", "notes")
    list_filter = ("date", "medication")
