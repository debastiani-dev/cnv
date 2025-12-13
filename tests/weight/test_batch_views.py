import uuid
from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.weight.models import WeighingSession, WeightRecord


@pytest.mark.django_db
class TestBatchWeighingView:
    """Tests for BatchWeighingView - batch weight entry functionality."""

    def test_get_batch_view_with_session_storage(self, client, user):
        """Test GET request retrieves cattle from session storage."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")
        cow2 = baker.make(Cattle, tag="COW002")

        # Set session storage
        s = client.session
        s["batch_weighing_cattle_ids"] = [str(cow1.pk), str(cow2.pk)]
        s.save()

        response = client.get(reverse("weight:batch-entry", kwargs={"pk": session.pk}))

        assert response.status_code == 200
        assert cow1 in response.context["cattle_list"]
        assert cow2 in response.context["cattle_list"]

    def test_get_batch_view_with_query_params(self, client, user):
        """Test GET request retrieves cattle from query parameters."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")
        cow2 = baker.make(Cattle, tag="COW002")

        response = client.get(
            reverse("weight:batch-entry", kwargs={"pk": session.pk})
            + f"?ids={cow1.pk},{cow2.pk}"
        )

        assert response.status_code == 200
        assert cow1 in response.context["cattle_list"]
        assert cow2 in response.context["cattle_list"]

    def test_get_batch_view_no_cattle_redirects(self, client, user):
        """Test GET request without cattle IDs redirects with warning."""
        client.force_login(user)
        session = baker.make(WeighingSession)

        response = client.get(reverse("weight:batch-entry", kwargs={"pk": session.pk}))

        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("no cattle selected" in str(m).lower() for m in messages)

    def test_post_batch_weights_success(self, client, user):
        """Test successful batch weight entry."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")
        cow2 = baker.make(Cattle, tag="COW002")

        data = {
            "cattle_ids": [str(cow1.pk), str(cow2.pk)],
            f"weight_{cow1.pk}": "450.5",
            f"weight_{cow2.pk}": "380.0",
        }

        response = client.post(
            reverse("weight:batch-entry", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        assert WeightRecord.objects.filter(session=session, animal=cow1).exists()
        assert WeightRecord.objects.filter(session=session, animal=cow2).exists()

        record1 = WeightRecord.objects.get(session=session, animal=cow1)
        assert record1.weight_kg == Decimal("450.5")

        messages = list(get_messages(response.wsgi_request))
        assert any("successfully" in str(m).lower() for m in messages)
        assert any("2 animals" in str(m).lower() for m in messages)

    def test_post_batch_weights_skip_empty(self, client, user):
        """Test that empty weight inputs are skipped."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")
        cow2 = baker.make(Cattle, tag="COW002")

        data = {
            "cattle_ids": [str(cow1.pk), str(cow2.pk)],
            f"weight_{cow1.pk}": "450.5",
            f"weight_{cow2.pk}": "",  # Empty - should be skipped
        }

        response = client.post(
            reverse("weight:batch-entry", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        assert WeightRecord.objects.filter(session=session, animal=cow1).exists()
        assert not WeightRecord.objects.filter(session=session, animal=cow2).exists()

    def test_post_batch_weights_invalid_weight(self, client, user):
        """Test handling of invalid weight input."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")

        data = {
            "cattle_ids": [str(cow1.pk)],
            f"weight_{cow1.pk}": "invalid",
        }

        response = client.post(
            reverse("weight:batch-entry", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        assert not WeightRecord.objects.filter(session=session, animal=cow1).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("error" in str(m).lower() for m in messages)

    def test_post_batch_weights_negative_weight(self, client, user):
        """Test handling of negative weight input."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")

        data = {
            "cattle_ids": [str(cow1.pk)],
            f"weight_{cow1.pk}": "-50",
        }

        response = client.post(
            reverse("weight:batch-entry", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        assert not WeightRecord.objects.filter(session=session, animal=cow1).exists()
        messages = list(get_messages(response.wsgi_request))
        assert any("error" in str(m).lower() for m in messages)

    def test_post_batch_weights_cattle_not_found(self, client, user):
        """Test handling of non-existent cattle ID."""
        client.force_login(user)
        session = baker.make(WeighingSession)

        fake_uuid = str(uuid.uuid4())

        data = {
            "cattle_ids": [fake_uuid],
            f"weight_{fake_uuid}": "450.5",
        }

        response = client.post(
            reverse("weight:batch-entry", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("error" in str(m).lower() for m in messages)

    def test_post_batch_weights_no_weights_recorded(self, client, user):
        """Test message when no weights are recorded."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")

        data = {
            "cattle_ids": [str(cow1.pk)],
            f"weight_{cow1.pk}": "",  # Empty
        }

        response = client.post(
            reverse("weight:batch-entry", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("no weights were recorded" in str(m).lower() for m in messages)

    def test_post_clears_session_storage(self, client, user):
        """Test that session storage is cleared after POST."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        cow1 = baker.make(Cattle, tag="COW001")

        # Set session storage
        s = client.session
        s["batch_weighing_cattle_ids"] = [str(cow1.pk)]
        s.save()

        data = {
            "cattle_ids": [str(cow1.pk)],
            f"weight_{cow1.pk}": "450.5",
        }

        response = client.post(
            reverse("weight:batch-entry", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        assert "batch_weighing_cattle_ids" not in client.session
