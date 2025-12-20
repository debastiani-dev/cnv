from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from .models.transaction import Transaction
from .models.transaction_item import TransactionItem
from .services.transaction_service import TransactionService


class TransactionItemInline(admin.TabularInline):
    model = TransactionItem
    extra = 1
    autocomplete_fields = ["transaction"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "type", "partner", "total_amount", "status"]
    list_filter = ["type", "status", "date"]
    search_fields = ["partner__name", "notes"]
    inlines = [TransactionItemInline]
    actions = ["confirm_transactions"]

    @admin.action(description=_("Confirm Selected Transactions"))
    def confirm_transactions(self, request, queryset):
        success_count = 0

        for tx in queryset:
            try:
                TransactionService.confirm_transaction(tx)
                success_count += 1
            except ValidationError as e:
                self.message_user(
                    request, f"Error confirming {tx}: {e}", level=messages.ERROR
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Unexpected error confirming {tx}: {e}",
                    level=messages.ERROR,
                )

        if success_count > 0:
            self.message_user(
                request,
                _("Successfully confirmed %(count)d transactions.")
                % {"count": success_count},
            )
