from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.cattle.models import Cattle
from apps.health.models import Medication, MedicationType, MedicationUnit
from apps.health.services.health_service import HealthService
from apps.partners.models import Partner
from apps.sales.models import Sale, SaleItem
from apps.sales.services.sale_service import SaleService


@pytest.mark.django_db
class TestSalesWithdrawalIntegration:
    def test_withdrawal_blocks_sale(self):
        """
        Verify that an animal under withdrawal cannot be added to a sale.
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
        with pytest.raises(ValidationError) as excinfo:
            SaleService.validate_item_for_sale(cow)

        assert "Sanitary Block" in str(excinfo.value)
        assert "Animal in withdrawal period" in str(excinfo.value)

        # 5. Attempt to Create Sale via Service (Integration)
        sale = Sale.objects.create(partner=partner, date=timezone.localdate())
        item = SaleItem(content_object=cow, quantity=1, unit_price=Decimal("1000.00"))

        with pytest.raises(ValidationError) as excinfo:
            SaleService.create_sale(sale, [item])

        assert "Sanitary Block" in str(excinfo.value)

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

        # 4. Validate
        try:
            SaleService.validate_item_for_sale(cow)
        except ValidationError:
            pytest.fail("Validation raised Error unexpectedly for expired withdrawal")

        # 5. Create Sale
        sale = Sale.objects.create(partner=partner, date=timezone.localdate())
        item = SaleItem(content_object=cow, quantity=1, unit_price=Decimal("1000.00"))

        # Should NOT raise
        SaleService.create_sale(sale, [item])

        assert sale.items.count() == 1

    def test_clean_animal_allows_sale(self):
        """
        Verify that an animal with NO events CAN be sold.
        """
        cow = Cattle.objects.create(tag="FRESH-001", birth_date=date(2023, 1, 1))
        SaleService.validate_item_for_sale(cow)  # Should pass
