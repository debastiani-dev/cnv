from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.commercial.models import SalesEvent, SalesLot
from apps.health.models import (
    Medication,
    MedicationType,
    MedicationUnit,
    SanitaryEvent,
    SanitaryEventTarget,
)


@pytest.mark.django_db
class TestDashboardWithdrawalKPI:
    def test_withdrawal_count_on_dashboard(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        # 1. Active Withdrawal
        cow1 = baker.make(
            Cattle,
            status=Cattle.STATUS_AVAILABLE,
            withdrawal_end_date=timezone.now().date() + timedelta(days=8),
        )
        med1 = baker.make(
            Medication,
            withdrawal_days_meat=10,
            unit=MedicationUnit.ML,
            medication_type=MedicationType.ANTIBIOTIC,
        )
        event1 = baker.make(
            SanitaryEvent,
            date=timezone.localdate() - timedelta(days=2),
            medication=med1,
            performed_by=user,
        )
        baker.make(SanitaryEventTarget, event=event1, animal=cow1)
        # End date = -2 + 10 = +8 days from now. Active.

        # 2. Expired Withdrawal
        cow2 = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)
        med2 = baker.make(
            Medication,
            withdrawal_days_meat=5,
            unit=MedicationUnit.ML,
            medication_type=MedicationType.ANTIBIOTIC,
        )
        event2 = baker.make(
            SanitaryEvent,
            date=timezone.localdate() - timedelta(days=10),
            medication=med2,
            performed_by=user,
        )
        baker.make(SanitaryEventTarget, event=event2, animal=cow2)
        # End date = -10 + 5 = -5 days from now. Expired.

        # 3. Clean Animal
        baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)

        # 4. Inactive (Dead/Sold) Animal with Withdrawal
        cow4 = baker.make(Cattle, status=Cattle.STATUS_DEAD)
        event4 = baker.make(
            SanitaryEvent, date=timezone.localdate(), medication=med1, performed_by=user
        )
        baker.make(SanitaryEventTarget, event=event4, animal=cow4)

        # Put cow1 (Active Withdrawal) on Sale to trigger ALERT
        event = baker.make(
            SalesEvent,
            date=timezone.now().date() + timedelta(days=1),
            sales_type=SalesEvent.TYPE_AUCTION,
            is_active=True,
        )
        lot = baker.make(
            SalesLot,
            event=event,
            status=SalesLot.STATUS_AVAILABLE,
        )
        lot.animals.add(cow1)

        # Request Dashboard
        response = client.get(reverse("dashboard:home"))
        assert response.status_code == 200

        # Check context
        # "active_withdrawal_count" is removed.
        # "recent_health_events" is removed.
        # We now check for Critical Alerts.
        assert "alerts" in response.context
        alerts = response.context["alerts"]

        # We expect a Safety Violation alert
        msg_list = [a["msg"] for a in alerts]
        assert any("SAFETY VIOLATION" in m for m in msg_list)
