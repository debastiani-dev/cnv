import pytest
from django.urls import reverse
from model_bakery import baker

from apps.tasks.models import Task


@pytest.mark.django_db
class TestTaskStatusUpdateAPI:
    def test_update_status_success(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)
        task = baker.make(Task, assigned_to=user, status=Task.Status.PENDING)

        url = reverse("tasks:api-update-status", args=[task.pk])
        payload = {"status": "DONE"}

        response = client.post(url, data=payload, content_type="application/json")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_status_display"] == "Done"
        assert "bg-green-50" in data["color_class"]

        task.refresh_from_db()
        assert task.status == Task.Status.DONE
        assert task.completed_at is not None

    def test_update_status_invalid_code(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)
        task = baker.make(Task, assigned_to=user)

        url = reverse("tasks:api-update-status", args=[task.pk])
        response = client.post(
            url, data={"status": "INVALID_CODE"}, content_type="application/json"
        )

        assert response.status_code == 400
        assert response.json()["error"] == "Invalid status code"

    def test_update_status_invalid_json(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)
        task = baker.make(Task, assigned_to=user)

        url = reverse("tasks:api-update-status", args=[task.pk])
        # Send raw string data that is not valid JSON
        response = client.post(
            url, data="not valid json", content_type="application/json"
        )

        assert response.status_code == 400
        assert response.json()["error"] == "Invalid JSON"

    def test_update_status_permission_denied(self, client, django_user_model):
        owner = baker.make(django_user_model)
        other_user = baker.make(django_user_model)
        client.force_login(other_user)

        # Task assigned to owner, other_user should not be able to edit
        task = baker.make(Task, assigned_to=owner)

        url = reverse("tasks:api-update-status", args=[task.pk])
        response = client.post(
            url, data={"status": "DONE"}, content_type="application/json"
        )

        # Expecting 403 Forbidden based on view implementation logic
        assert response.status_code == 403

    def test_update_status_not_assigned_allows_fallback(
        self, client, django_user_model
    ):
        # If no strict rule for unassigned tasks, verify behavior.
        # Current logic: "if task.assigned_to and task.assigned_to != request.user ..."
        # So unassigned tasks might be editable by anyone logged in?
        # Let's verify current implementation behavior.
        user = baker.make(django_user_model)
        client.force_login(user)
        task = baker.make(Task, assigned_to=None)

        url = reverse("tasks:api-update-status", args=[task.pk])
        response = client.post(
            url, data={"status": "IN_PROGRESS"}, content_type="application/json"
        )

        assert response.status_code == 200
        task.refresh_from_db()
        assert task.status == Task.Status.IN_PROGRESS
