from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.health.models import Medication
from apps.health.services import HealthService


@pytest.mark.django_db
class TestSanitaryEventCRUD:
    def test_update_event_remove_target_recalculates_cost(
        self, client, django_user_model
    ):
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        # 1. Create Data
        medication = baker.make(Medication, name="Meds", withdrawal_days_meat=10)
        cattle = baker.make(Cattle, _quantity=2, status=Cattle.STATUS_AVAILABLE)

        # 2. Create Event (Batch)
        event_data = {
            "date": date.today(),
            "title": "Vaccination",
            "medication": medication,
            "total_cost": Decimal("100.00"),
            "performed_by": user,
        }
        cattle_uuids = [c.pk for c in cattle]
        event = HealthService.create_batch_event(event_data, cattle_uuids)

        # Verify initial state
        assert event.targets.count() == 2
        assert event.targets.first().cost_per_head == Decimal("50.00")

        # 3. Update: Remove one target
        url = reverse("health:event-update", kwargs={"pk": event.pk})
        target_to_remove = event.targets.first()

        data = {
            "date": event.date,
            "title": "Vaccination Updated",
            "medication": medication.pk,
            "total_cost": "100.00",
            "remove_targets": [target_to_remove.pk],
        }

        response = client.post(url, data)
        assert response.status_code == 302

        # 4. Verify Result
        event.refresh_from_db()
        assert event.title == "Vaccination Updated"
        assert event.targets.count() == 1

        remaining_target = event.targets.first()
        assert remaining_target.pk != target_to_remove.pk
        # Cost should now be 100 for the single remaining animal
        assert remaining_target.cost_per_head == Decimal("100.00")

    def test_delete_event_clears_withdrawal(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        # 1. Create Data
        medication = baker.make(Medication, name="Meds", withdrawal_days_meat=10)
        cow = baker.make(Cattle, status=Cattle.STATUS_AVAILABLE)

        # 2. Create Event with withdrawal
        event_data = {
            "date": date.today(),
            "title": "Withdrawal Event",
            "medication": medication,
            "total_cost": 0,
            "performed_by": user,
        }
        event = HealthService.create_batch_event(event_data, [cow.pk])

        # Verify blocked
        is_blocked, _ = HealthService.check_withdrawal_status(cow)
        assert is_blocked is True

        # 3. Delete Event via View
        url = reverse("health:event-delete", kwargs={"pk": event.pk})
        response = client.post(url)
        assert response.status_code == 302

        # 4. Verify Soft Delete
        event.refresh_from_db()
        assert event.is_deleted is True

        # 5. Verify NOT Blocked anymore
        is_blocked, _ = HealthService.check_withdrawal_status(cow)
        assert is_blocked is False
