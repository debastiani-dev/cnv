import pytest
from django.urls import reverse
from model_bakery import baker

from apps.authentication.models import User
from apps.cattle.models import Cattle
from apps.health.models import HealthProtocol, Medication, MedicationType, SanitaryEvent


@pytest.mark.django_db
class TestProtocolApplyView:
    def setup_method(self):
        self.url = reverse("health:protocol-apply")
        self.user = baker.make(User, username="testuser")
        self.protocol = baker.make(HealthProtocol, name="Test Protocol", is_active=True)
        # Add item to protocol
        self.medication = baker.make(
            Medication, name="Med1", medication_type=MedicationType.VACCINE
        )
        baker.make(
            "health.ProtocolItem",
            protocol=self.protocol,
            medication=self.medication,
            default_dosage="10ml",
        )
        self.cattle_list = baker.make(Cattle, _quantity=3)
        self.cattle_ids = [c.pk for c in self.cattle_list]

    def test_apply_view_setup_phase(self, client):
        """Test the initial POST from cattle list (Setup Phase)"""
        client.force_login(self.user)
        data = {"cattle_ids": self.cattle_ids}
        response = client.post(self.url, data)

        assert response.status_code == 200
        assert "health/protocol_apply.html" in [t.name for t in response.templates]
        assert response.context["cattle_count"] == 3
        # Check hidden inputs are present in HTML (simplified check)
        assert f'value="{self.cattle_ids[0]}"' in str(
            response.content
        ) or f'value="{",".join(map(str, self.cattle_ids))}"' in str(response.content)

    def test_apply_view_perform_phase(self, client):
        """Test the final POST to apply protocol (Perform Phase)"""
        client.force_login(self.user)

        cattle_ids_str = ",".join(map(str, self.cattle_ids))
        data = {
            "perform_application": "1",
            "cattle_ids_str": cattle_ids_str,
            "protocol": self.protocol.pk,
            "date": "2023-10-27",
            "performed_by": self.user.pk,
        }

        response = client.post(self.url, data, follow=True)

        assert response.status_code == 200  # Redirect followed

        # Check assertions
        assert SanitaryEvent.objects.count() == 1  # 1 Header Event
        event = SanitaryEvent.objects.first()
        assert event.targets.count() == 3  # 3 Cattle Targets

    def test_apply_view_no_cattle_selected(self, client):
        client.force_login(self.user)
        data = {}  # No cattle_ids
        response = client.post(self.url, data, follow=True)
        # Should redirect back to list with warning
        assert response.status_code == 200
