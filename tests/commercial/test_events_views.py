# pylint: disable=redefined-outer-name
import uuid
from unittest.mock import patch

import pytest
from django.urls import reverse
from model_bakery import baker

from apps.authentication.models.user import User
from apps.commercial.models import SalesEvent


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="password")


@pytest.fixture
def client(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestSalesEventListView:
    def test_filter_by_query(self, client):
        baker.make(SalesEvent, name="Alpha Auction", description="First")
        baker.make(SalesEvent, name="Beta Sale", description="Second")

        url = reverse("commercial:event_list")
        response = client.get(url, {"q": "Alpha"})

        assert response.status_code == 200
        assert len(response.context["events"]) == 1
        assert response.context["events"][0].name == "Alpha Auction"

        response = client.get(url, {"q": "Second"})
        assert len(response.context["events"]) == 1
        assert response.context["events"][0].name == "Beta Sale"

    def test_filter_by_date(self, client):
        e1 = baker.make(SalesEvent, date="2023-01-01")
        e2 = baker.make(SalesEvent, date="2023-02-01")

        url = reverse("commercial:event_list")
        # Date After
        response = client.get(url, {"date_after": "2023-01-15"})
        assert len(response.context["events"]) == 1
        assert response.context["events"][0] == e2

        # Date Before
        response = client.get(url, {"date_before": "2023-01-15"})
        assert len(response.context["events"]) == 1
        assert response.context["events"][0] == e1


@pytest.mark.django_db
class TestSalesEventCreateUpdateView:
    def test_create_view_success_message(self, client):
        url = reverse("commercial:event_create")
        data = {
            "name": "New Event",
            "date": "2023-10-10",
            "sales_type": SalesEvent.TYPE_AUCTION,
            "description": "Desc",
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) == 1
        assert str(messages[0]) == "Event created successfully."

    def test_create_view_get(self, client):
        """Test GET request to cover get_context_data."""
        url = reverse("commercial:event_create")
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["title"] == "Create Sales Event"

    def test_update_view_success_message(self, client):
        event = baker.make(SalesEvent)
        url = reverse("commercial:event_update", kwargs={"pk": event.pk})
        data = {
            "name": "Updated Event",
            "date": event.date,
            "sales_type": event.sales_type,
            "description": "Updated",
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) == 1
        assert str(messages[0]) == "Event updated successfully."

    def test_update_view_get(self, client):
        """Test GET request to cover get_context_data."""
        event = baker.make(SalesEvent)
        url = reverse("commercial:event_update", kwargs={"pk": event.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["title"] == "Edit Sales Event"


@pytest.mark.django_db
class TestSalesEventToggleActiveView:
    def test_toggle_success(self, client):
        event = baker.make(SalesEvent, is_active=True)
        url = reverse("commercial:event_toggle_active", kwargs={"pk": event.pk})

        response = client.post(url)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["is_active"] is False

        event.refresh_from_db()
        assert event.is_active is False

    def test_toggle_not_found(self, client):
        url = reverse("commercial:event_toggle_active", kwargs={"pk": uuid.uuid4()})
        response = client.post(url)
        assert response.status_code == 404
        assert response.json()["message"] == "Event not found"

    def test_toggle_exception(self, client):
        # Mock save to raise exception
        event = baker.make(SalesEvent)
        url = reverse("commercial:event_toggle_active", kwargs={"pk": event.pk})

        with patch.object(SalesEvent, "save", side_effect=Exception("DB Error")):
            response = client.post(url)
            assert response.status_code == 500
            assert response.json()["message"] == "DB Error"
