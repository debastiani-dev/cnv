from django.contrib import admin
from apps.partners.models import Partner

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "tax_id", "email", "phone", "is_customer", "is_supplier")
    list_filter = ("is_customer", "is_supplier")
    search_fields = ("name", "tax_id", "email")
