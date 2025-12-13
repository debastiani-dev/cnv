import datetime

import pytest
from django.urls import reverse
from model_bakery import baker

from apps.weight.models import WeighingSession, WeighingSessionType


@pytest.mark.django_db
class TestWeighingSessionListView:
    def test_list_view_filters(self, client, user):
        """Test list view filters: search, type, date."""
        client.force_login(user)

        # Setup data
        s1 = baker.make(
            WeighingSession,
            name="Alpha Session",
            session_type=WeighingSessionType.ROUTINE,
            date=datetime.date(2024, 1, 1),
        )
        s2 = baker.make(
            WeighingSession,
            name="Beta Session",
            session_type=WeighingSessionType.WEANING,
            date=datetime.date(2024, 2, 1),
        )

        base_url = reverse("weight:session-list")

        # 1. Search (name)
        response = client.get(base_url, {"q": "Alpha"})
        assert s1 in response.context["sessions"]
        assert s2 not in response.context["sessions"]

        # 2. Type Filter
        response = client.get(base_url, {"type": WeighingSessionType.WEANING})
        assert s1 not in response.context["sessions"]
        assert s2 in response.context["sessions"]

        # 3. Date Range
        # After Jan 15 -> Only Feb
        response = client.get(base_url, {"date_after": "2024-01-15"})
        assert s1 not in response.context["sessions"]
        assert s2 in response.context["sessions"]

        # Before Jan 15 -> Only Jan
        response = client.get(base_url, {"date_before": "2024-01-15"})
        assert s1 in response.context["sessions"]
        assert s2 not in response.context["sessions"]


@pytest.mark.django_db
class TestWeighingSessionCreateView:
    def test_context_cattle_ids(self, client, user):
        """Test that cattle_ids in GET are passed to context."""
        client.force_login(user)
        url = reverse("weight:session-create")

        response = client.get(url, {"cattle_ids": ["uuid-1", "uuid-2"]})
        assert response.status_code == 200
        assert "uuid-1" in response.context["cattle_ids"]
        assert "uuid-2" in response.context["cattle_ids"]

    def test_create_without_cattle_ids(self, client, user):
        """Test creating session without cattle redirects to detail."""
        client.force_login(user)
        url = reverse("weight:session-create")
        data = {
            "name": "Plain Session",
            "date": "2024-03-01",
            "session_type": WeighingSessionType.ROUTINE,
        }

        response = client.post(url, data)
        assert response.status_code == 302
        session = WeighingSession.objects.get(name="Plain Session")
        assert response.url == reverse(
            "weight:session-detail", kwargs={"pk": session.pk}
        )
