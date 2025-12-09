from datetime import date
from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.cattle.models import Cattle
from apps.health.models import Medication, MedicationType, MedicationUnit, SanitaryEvent


@pytest.mark.django_db
class TestMedicationProtection:
    def test_cannot_delete_medication_in_use(self, client, django_user_model):
        # 1. Setup User & Login
        user = django_user_model.objects.create_user(
            username="vet_user", password="password"
        )
        client.force_login(user)

        # 2. Create Medication
        med = Medication.objects.create(
            name="Protected Med Test",
            medication_type=MedicationType.VACCINE,
            unit=MedicationUnit.ML,
            withdrawal_days_meat=10,
        )

        # 3. Create Cattle & Sanitary Event using Med
        Cattle.objects.create(tag="COW-001", birth_date=date(2023, 1, 1))
        SanitaryEvent.objects.create(
            date=date.today(),
            title="Vaccination Event",
            medication=med,
            total_cost=Decimal("50.00"),
        )

        # 4. Try to Delete
        delete_url = reverse("health:medication-delete", kwargs={"pk": med.pk})
        response = client.post(delete_url, follow=True)

        # 5. Verify
        # Should redirect back to list
        assert response.redirect_chain[-1][0] == reverse("health:medication-list")

        # Check if medication was actually deleted
        med_exists = Medication.objects.filter(pk=med.pk).exists()
        assert med_exists

        # Should have error message
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "Cannot delete this medication" in str(messages[0])

        # Medication should still exist
        assert Medication.objects.filter(pk=med.pk).exists()

    def test_can_delete_unused_medication(self, client, django_user_model):
        # 1. Setup
        user = django_user_model.objects.create_user(
            username="vet_user2", password="password"
        )
        client.force_login(user)

        # 2. Create Med
        med = Medication.objects.create(name="Transient Med")

        # 3. Delete
        delete_url = reverse("health:medication-delete", kwargs={"pk": med.pk})
        client.post(delete_url, follow=True)

        # 4. Verify
        assert not Medication.objects.filter(pk=med.pk).exists()
