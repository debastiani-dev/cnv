from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.health.models import Medication, SanitaryEvent, SanitaryEventTarget
from apps.sales.models import Sale, SaleItem
from apps.sales.services.sale_service import SaleService


@pytest.mark.django_db
class TestSaleWithdrawalIntegration:
    def test_create_sale_blocks_if_animal_in_withdrawal(self):
        # 1. Setup Animal in Withdrawal
        cow = baker.make(Cattle)
        med = baker.make(Medication, withdrawal_days_meat=20, name="Blocker")

        # Event 5 days ago (Active)
        event_date = timezone.localdate() - timedelta(days=5)
        event = baker.make(SanitaryEvent, date=event_date, medication=med)
        baker.make(SanitaryEventTarget, event=event, animal=cow)

        # 2. Attempt to sell
        sale = baker.make(Sale)
        item = SaleItem(content_object=cow, quantity=1, unit_price=1000)

        # 3. Verify Error
        with pytest.raises(ValidationError) as exc:
            SaleService.create_sale(sale, [item])

        assert "Animal in withdrawal period" in str(exc.value)
        assert "Blocker" in str(exc.value)

    def test_create_sale_allows_if_withdrawal_expired(self):
        # 1. Setup Animal with Expired Withdrawal
        cow = baker.make(Cattle)
        med = baker.make(Medication, withdrawal_days_meat=5)

        # Event 10 days ago (Expired)
        event_date = timezone.localdate() - timedelta(days=10)
        event = baker.make(SanitaryEvent, date=event_date, medication=med)
        baker.make(SanitaryEventTarget, event=event, animal=cow)

        # 2. Attempt to sell
        sale = baker.make(Sale)
        item = SaleItem(content_object=cow, quantity=1, unit_price=1000)

        # 3. Should succeed
        result = SaleService.create_sale(sale, [item])
        assert result.pk is not None
        assert result.items.count() == 1
