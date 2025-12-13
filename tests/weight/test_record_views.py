import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from model_bakery import baker

from apps.weight.models import WeightRecord


@pytest.mark.django_db
class TestWeightRecordViews:
    def test_update_context_and_message(self, client, user):
        """Test update view context and success message."""
        client.force_login(user)
        record = baker.make(WeightRecord)

        url = reverse("weight:record-update", kwargs={"pk": record.pk})

        # Context
        response = client.get(url)
        assert response.status_code == 200
        assert "Edit Weight Record" in response.context["title"]

        # Message
        data = {
            "weight_kg": record.weight_kg + 10,
            "session": record.session.pk,
            "animal": record.animal.pk,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("updated" in str(m).lower() for m in messages)

    def test_delete_last_record_constraint(self, client, user):
        """Test that the last record in a session cannot be deleted."""
        client.force_login(user)
        session = baker.make("weight.WeighingSession")
        record = baker.make(WeightRecord, session=session)

        # Only 1 record in session
        assert session.records.count() == 1

        url = reverse("weight:record-delete", kwargs={"pk": record.pk})

        # Post to delete
        response = client.post(url)
        assert response.status_code == 302  # Redirects anyway

        # Verify Not Deleted
        assert WeightRecord.objects.filter(pk=record.pk).exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("cannot delete the last record" in str(m).lower() for m in messages)

    def test_delete_record_success(self, client, user):
        """Test that record can be deleted if multiple exist."""
        client.force_login(user)
        session = baker.make("weight.WeighingSession")
        r1 = baker.make(WeightRecord, session=session)
        r2 = baker.make(WeightRecord, session=session)

        assert session.records.count() == 2

        url = reverse("weight:record-delete", kwargs={"pk": r1.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert not WeightRecord.objects.filter(pk=r1.pk).exists()
        assert WeightRecord.objects.filter(pk=r2.pk).exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("deleted" in str(m).lower() for m in messages)
