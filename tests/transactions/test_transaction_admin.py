from unittest.mock import MagicMock, patch

import pytest
from django.contrib.admin import AdminSite
from django.core.exceptions import ValidationError
from model_bakery import baker

from apps.transactions.admin import TransactionAdmin
from apps.transactions.models import Transaction
from apps.transactions.services.transaction_service import TransactionService


@pytest.mark.django_db
class TestTransactionAdmin:
    def test_confirm_transactions_success(self):
        site = AdminSite()
        admin = TransactionAdmin(Transaction, site)
        admin.message_user = MagicMock()  # Mock message_user on the instance

        tx = baker.make(Transaction, status=Transaction.STATUS_DRAFT)
        queryset = Transaction.objects.filter(pk=tx.pk)

        request = MagicMock()

        with patch.object(TransactionService, "confirm_transaction") as mock_confirm:
            admin.confirm_transactions(request, queryset)
            mock_confirm.assert_called_once_with(tx)

            # Verify success message
            assert admin.message_user.called
            args, _ = admin.message_user.call_args
            assert "Successfully confirmed 1 transactions" in str(args[1])

    def test_confirm_transactions_validation_error(self):
        site = AdminSite()
        admin = TransactionAdmin(Transaction, site)
        admin.message_user = MagicMock()

        tx = baker.make(Transaction, status=Transaction.STATUS_DRAFT)
        queryset = Transaction.objects.filter(pk=tx.pk)
        request = MagicMock()

        with patch.object(
            TransactionService,
            "confirm_transaction",
            side_effect=ValidationError("Mock Validation Error"),
        ):
            admin.confirm_transactions(request, queryset)

            # Verify error message
            assert admin.message_user.called
            args, kwargs = admin.message_user.call_args
            assert "Error confirming" in str(args[1])
            assert "Mock Validation Error" in str(args[1])
            assert kwargs["level"] == 40  # messages.ERROR

    def test_confirm_transactions_unexpected_error(self):
        site = AdminSite()
        admin = TransactionAdmin(Transaction, site)
        admin.message_user = MagicMock()

        tx = baker.make(Transaction, status=Transaction.STATUS_DRAFT)
        queryset = Transaction.objects.filter(pk=tx.pk)
        request = MagicMock()

        with patch.object(
            TransactionService,
            "confirm_transaction",
            side_effect=Exception("Unexpected Crash"),
        ):
            admin.confirm_transactions(request, queryset)

            # Verify error message
            assert admin.message_user.called
            args, kwargs = admin.message_user.call_args
            assert "Unexpected error confirming" in str(args[1])
            assert "Unexpected Crash" in str(args[1])
