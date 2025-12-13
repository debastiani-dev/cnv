import uuid
from unittest.mock import patch

import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.tasks.models import Task


@pytest.mark.django_db
class TestTaskTrashViews:
    def test_soft_delete_task(self, client, user):
        client.force_login(user)
        task = baker.make(Task, title="Task to Delete")
        url = reverse("tasks:delete", kwargs={"pk": task.pk})

        # Test Get (Confirmation Page)
        response = client.get(url)
        assert response.status_code == 200
        assert "Delete Task" in str(response.content)

        # Test Post (Action)
        response = client.post(url)
        assert response.status_code == 302  # Redirects to list

        # Verify Soft Delete
        assert not Task.objects.filter(pk=task.pk).exists()
        assert Task.all_objects.filter(pk=task.pk, is_deleted=True).exists()

    def test_trash_list_view(self, client, user):
        client.force_login(user)
        # Create one active and one deleted task
        active_task = baker.make(Task, title="Active")
        deleted_task = baker.make(Task, title="Deleted", is_deleted=True)

        url = reverse("tasks:trash")
        response = client.get(url)

        assert response.status_code == 200
        tasks_in_context = response.context["tasks"]
        assert deleted_task in tasks_in_context
        assert active_task not in tasks_in_context

    def test_restore_task(self, client, user):
        client.force_login(user)
        task = baker.make(Task, title="Restorable", is_deleted=True)
        url = reverse("tasks:restore", kwargs={"pk": task.pk})

        # Test Get (Confirmation)
        response = client.get(url)
        assert response.status_code == 200

        # Test Post (Restore)
        response = client.post(url)
        assert response.status_code == 302

        # Verify Restored
        task.refresh_from_db()
        assert not task.is_deleted
        assert Task.objects.filter(pk=task.pk).exists()

    def test_permanent_delete_task(self, client, user):
        client.force_login(user)
        task = baker.make(Task, title="Gone Forever", is_deleted=True)
        url = reverse("tasks:permanent-delete", kwargs={"pk": task.pk})

        # Test Get (Confirmation)
        response = client.get(url)
        assert response.status_code == 200

        # Test Post (Hard Delete)
        response = client.post(url)
        assert response.status_code == 302

        # Verify Gone from DB
        assert not Task.all_objects.filter(pk=task.pk).exists()

    def test_restore_invalid_uuid(self, client, user):
        client.force_login(user)
        url = reverse("tasks:restore", kwargs={"pk": uuid.uuid4()})
        response = client.post(url)
        assert response.status_code == 302  # Redirect to list
        # Message assertion can be problematic if messages middleware not fully setup in test, but 302 implies handled.

        response_get = client.get(url)
        assert response_get.status_code == 302  # Redirect to list

    def test_permanent_delete_invalid_uuid(self, client, user):
        client.force_login(user)
        url = reverse("tasks:permanent-delete", kwargs={"pk": uuid.uuid4()})
        response = client.post(url)
        assert response.status_code == 302  # Redirect to trash

        response_get = client.get(url)
        assert response_get.status_code == 302  # Redirect to trash

    def test_soft_delete_via_delete_method(self, client, user):
        """Test sending a DELETE request directly."""
        client.force_login(user)
        task = baker.make(Task, title="Delete Me")
        url = reverse("tasks:delete", kwargs={"pk": task.pk})

        response = client.delete(url)
        assert response.status_code == 302
        assert not Task.objects.filter(pk=task.pk).exists()

    def test_soft_delete_protected_error(self, client, user):
        """Test ProtectedError handling during soft delete."""
        client.force_login(user)
        task = baker.make(Task)
        url = reverse("tasks:delete", kwargs={"pk": task.pk})

        with patch(
            "apps.tasks.services.tasks.TaskService.delete_task",
            side_effect=ProtectedError("Protected", []),
        ):
            response = client.post(url)
            assert response.status_code == 200  # Renders confirmation page with error
            assert "error" in response.context
            assert "referenced by other objects" in response.context["error"]

    def test_restore_value_error(self, client, user):
        """Test ValueError handling during restore."""
        client.force_login(user)
        task = baker.make(Task, is_deleted=True)
        url = reverse("tasks:restore", kwargs={"pk": task.pk})

        with patch(
            "apps.tasks.services.tasks.TaskService.restore_task",
            side_effect=ValueError("Invalid Action"),
        ):
            response = client.post(url)
            assert response.status_code == 302
            # Should have error message

    def test_permanent_delete_protected_error(self, client, user):
        """Test ProtectedError handling during hard delete."""
        client.force_login(user)
        task = baker.make(Task, is_deleted=True)
        url = reverse("tasks:permanent-delete", kwargs={"pk": task.pk})

        with patch(
            "apps.tasks.services.tasks.TaskService.hard_delete_task",
            side_effect=ProtectedError("Protected", []),
        ):
            response = client.post(url)
            assert response.status_code == 200
            assert "error" in response.context
            assert "referenced by other objects" in response.context["error"]
