import datetime
import uuid
from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.weight.models import WeighingSession, WeighingSessionType
from tests.test_utils import verify_redirect_with_message


@pytest.mark.django_db
class TestWeighingSessionUpdateView:
    def test_update_view_context_data(self, client, user):
        """Test that update view context contains expected title."""
        client.force_login(user)
        session = baker.make(WeighingSession)

        response = client.get(
            reverse("weight:session-update", kwargs={"pk": session.pk})
        )

        assert response.status_code == 200
        assert "Edit Weighing Session" in response.context["title"]

    def test_update_view_success_message(self, client, user):
        """Test that update view adds success message."""
        client.force_login(user)
        session = baker.make(WeighingSession, date=datetime.date(2024, 1, 1))

        data = {
            "name": "Updated Name",
            "date": "2024-01-01",
            "session_type": WeighingSessionType.ROUTINE,
            "notes": "Updated notes",
        }

        response = client.post(
            reverse("weight:session-update", kwargs={"pk": session.pk}), data
        )

        assert response.status_code == 302
        messages = list(get_messages(response.wsgi_request))
        assert any("updated successfully" in str(m).lower() for m in messages)


@pytest.mark.django_db
class TestWeighingSessionTrashListView:
    def test_trash_list_view(self, client, user):
        """Test that trash list view displays deleted sessions."""
        client.force_login(user)
        active_session = baker.make(WeighingSession, name="Active")
        deleted_session = baker.make(WeighingSession, name="Deleted")
        deleted_session.delete()

        response = client.get(reverse("weight:session-trash"))

        assert response.status_code == 200
        assert deleted_session in response.context["sessions"]
        assert active_session not in response.context["sessions"]


@pytest.mark.django_db
class TestWeighingSessionRestoreView:
    def test_soft_delete_get_not_found(self, client, user):
        """Test GET request soft delete handles non-existent session."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("weight:session-delete", kwargs={"pk": fake_uuid})

        response = client.get(url)
        assert response.status_code == 404

    def test_restore_view_not_found(self, client, user):
        """Test restore view handles non-existent session ID."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("weight:session-restore", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="post")


@pytest.mark.django_db
class TestWeighingSessionDeleteView:
    def test_delete_view_get_confirmation(self, client, user):
        """Test GET request to delete view shows confirmation."""
        client.force_login(user)
        session = baker.make(WeighingSession)

        url = reverse("weight:session-delete", kwargs={"pk": session.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "delete" in response.content.decode().lower()

    def test_delete_view_verb(self, client, user):
        """Test DELETE verb request."""
        client.force_login(user)
        session = baker.make(WeighingSession)

        url = reverse("weight:session-delete", kwargs={"pk": session.pk})
        response = client.delete(url)

        assert response.status_code == 302
        assert not WeighingSession.objects.filter(pk=session.pk).exists()

    def test_delete_view_exception(self, client, user):
        """Test delete view handles exceptions."""
        client.force_login(user)
        session = baker.make(WeighingSession)

        with patch.object(
            WeighingSession, "soft_delete", side_effect=ValidationError("Error")
        ):
            response = client.post(
                reverse("weight:session-delete", kwargs={"pk": session.pk})
            )

        assert response.status_code == 200
        assert "Error" in response.content.decode()


@pytest.mark.django_db
class TestWeighingSessionHardDeleteView:
    def test_hard_delete_get_confirmation(self, client, user):
        """Test GET request to hard delete view shows confirmation."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        session.delete()  # Soft delete first

        response = client.get(
            reverse("weight:session-hard-delete", kwargs={"pk": session.pk})
        )

        assert response.status_code == 200
        assert session == response.context["session"]
        assert "confirm" in response.content.decode().lower()

    def test_hard_delete_get_not_found(self, client, user):
        """Test GET request handles non-existent session."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("weight:session-hard-delete", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="get")

    def test_hard_delete_post_not_found(self, client, user):
        """Test POST request handles non-existent session."""
        client.force_login(user)

        fake_uuid = str(uuid.uuid4())
        url = reverse("weight:session-hard-delete", kwargs={"pk": fake_uuid})
        verify_redirect_with_message(client, url, "not found", method="post")

    def test_hard_delete_view_exception(self, client, user):
        """Test hard delete view handles exceptions."""
        client.force_login(user)
        session = baker.make(WeighingSession)
        session.delete()

        with patch.object(
            WeighingSession, "delete", side_effect=ProtectedError("Protected", [])
        ):
            response = client.post(
                reverse("weight:session-hard-delete", kwargs={"pk": session.pk})
            )

        assert response.status_code == 200
        assert "confirm" in response.content.decode().lower()
        assert "referenced by other objects" in response.content.decode().lower()
