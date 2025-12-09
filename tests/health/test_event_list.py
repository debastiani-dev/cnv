import pytest
from django.urls import reverse
from model_bakery import baker

from apps.health.models import SanitaryEvent


@pytest.mark.django_db
class TestSanitaryEventListView:
    def test_list_view_access(self, client, django_user_model):
        """Test that the list view is accessible to logged-in users."""
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        url = reverse("health:event-list")
        response = client.get(url)

        assert response.status_code == 200
        assert "health/event_list.html" in [t.name for t in response.templates]

    def test_list_view_context(self, client, django_user_model):
        """Test that the list view contains events."""
        user = django_user_model.objects.create_user(
            username="testuser", password="password"
        )
        client.force_login(user)

        # Create events
        baker.make(SanitaryEvent, _quantity=3, title="Test Event", performed_by=user)

        url = reverse("health:event-list")
        response = client.get(url)

        assert len(response.context["events"]) == 3
        # Check annotation (not stricly necessary if baker doesn't add targets, but good to check access)
        assert hasattr(response.context["events"][0], "animal_count")
