from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.cattle.models import Cattle
from apps.health.models import Medication, MedicationType, MedicationUnit
from apps.health.services.health_service import HealthService
from apps.partners.models import Partner
from apps.transactions.models import Transaction, TransactionItem
from apps.transactions.services.transaction_service import TransactionService


@pytest.mark.django_db
class TestTransactionWithdrawalIntegration:
    def test_withdrawal_blocks_sale_transaction(self):
        """
        Verify that an animal under withdrawal cannot be added to a SALE transaction.
        """
        # 1. Setup Data
        partner = Partner.objects.create(name="Buyer Inc", email="buyer@example.com")
        cow = Cattle.objects.create(tag="BLOCKED-001", birth_date=date(2023, 1, 1))

        # 2. Medication with 30 days withdrawal
        med = Medication.objects.create(
            name="Strong Antibiotic",
            medication_type=MedicationType.ANTIBIOTIC,
            unit=MedicationUnit.ML,
            withdrawal_days_meat=30,
        )

        # 3. Apply Event TODAY
        HealthService.create_batch_event(
            event_data={
                "date": timezone.localdate(),
                "title": "Treatment",
                "medication": med,
                "total_cost": Decimal("10.00"),
            },
            cattle_uuids=[cow.pk],
        )

        # 4. Attempt to Validate for Sale
        # Assuming TransactionService exposes this, or checking via confirm
        # If confirm_transaction runs validation, we should try that.

        tx = Transaction.objects.create(
            partner=partner,
            date=timezone.localdate(),
            type=Transaction.TYPE_SALE,
            status=Transaction.STATUS_DRAFT,
        )
        TransactionItem.objects.create(
            transaction=tx,
            content_object=cow,
            quantity=1,
            unit_price=Decimal("1000.00"),
        )

        with pytest.raises(ValidationError) as excinfo:
            TransactionService.confirm_transaction(tx)

        # Check for specific error messages (adapted from old test)
        # Note: The error might be "Item X is not available: Animal in withdrawal..."
        err_msg = str(excinfo.value)
        assert "Sanitary Block" in err_msg or "withdrawal" in err_msg.lower()

    def test_expired_withdrawal_allows_sale(self):
        """
        Verify that an animal with EXPIRED withdrawal CAN be sold.
        """
        # 1. Setup
        partner = Partner.objects.create(name="Buyer Inc", email="buyer@example.com")
        cow = Cattle.objects.create(tag="CLEAN-001", birth_date=date(2023, 1, 1))

        # 2. Medication with 10 days withdrawal
        med = Medication.objects.create(
            name="Fast Antibiotic",
            medication_type=MedicationType.ANTIBIOTIC,
            unit=MedicationUnit.ML,
            withdrawal_days_meat=10,
        )

        # 3. Apply Event 20 DAYS AGO
        past_date = timezone.localdate() - timedelta(days=20)
        HealthService.create_batch_event(
            event_data={
                "date": past_date,
                "title": "Old Treatment",
                "medication": med,
                "total_cost": Decimal("10.00"),
            },
            cattle_uuids=[cow.pk],
        )

        # 4. Create Sale
        tx = Transaction.objects.create(
            partner=partner,
            date=timezone.localdate(),
            type=Transaction.TYPE_SALE,
            status=Transaction.STATUS_DRAFT,
        )
        TransactionItem.objects.create(
            transaction=tx,
            content_object=cow,
            quantity=1,
            unit_price=Decimal("1000.00"),
        )

        # 5. Confirm - Should NOT raise
        TransactionService.confirm_transaction(tx)

        tx.refresh_from_db()
        assert tx.status == Transaction.STATUS_CONFIRMED

    def test_clean_animal_allows_sale(self):
        """
        Verify that an animal with NO events CAN be sold.
        """
        partner = Partner.objects.create(name="Buyer Inc")
        cow = Cattle.objects.create(tag="FRESH-001", birth_date=date(2023, 1, 1))

        tx = Transaction.objects.create(
            partner=partner,
            date=timezone.localdate(),
            type=Transaction.TYPE_SALE,
            status=Transaction.STATUS_DRAFT,
        )
        TransactionItem.objects.create(
            transaction=tx,
            content_object=cow,
            quantity=1,
            unit_price=Decimal("1000.00"),
        )

        TransactionService.confirm_transaction(tx)
        assert tx.status == Transaction.STATUS_CONFIRMED
