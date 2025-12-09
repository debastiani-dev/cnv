from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
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
        cow1 = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)
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

        # Request Dashboard
        response = client.get(reverse("dashboard:home"))
        assert response.status_code == 200

        # Check context
        assert response.context["active_withdrawal_count"] == 1
        assert "recent_health_events" in response.context
        # We created 3 events (event1, event2, event4).
        # event1: -2 days
        # event2: -10 days
        # event4: today
        # Order should be event4, event1, event2
        recent = response.context["recent_health_events"]
        assert len(recent) == 3
        assert recent[0] == event4
        assert recent[1] == event1
        assert recent[2] == event2
