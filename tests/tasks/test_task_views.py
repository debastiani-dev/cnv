import pytest
from django.urls import reverse

from apps.tasks.models import Task


@pytest.mark.django_db
class TestTaskViews:
    def test_task_list_view(self, client, user):
        client.force_login(user)
        url = reverse("tasks:list")
        response = client.get(url)
        assert response.status_code == 200

    def test_task_create_view(self, client, user):
        client.force_login(user)
        url = reverse("tasks:create")
        data = {
            "title": "New Integration Task",
            "due_date": "2025-01-01",
            "priority": Task.Priority.MEDIUM,
            "status": Task.Status.PENDING,
            "assigned_to": user.pk,
        }
        response = client.post(url, data)
        assert response.status_code == 302  # Redirects to calendar
        assert Task.objects.filter(title="New Integration Task").exists()

    def test_task_api_events(self, client, user):
        client.force_login(user)
        Task.objects.create(title="API Task", due_date="2025-01-15", assigned_to=user)
        url = reverse("tasks:api-events")
        response = client.get(url, {"start": "2025-01-01", "end": "2025-01-31"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "API Task"
        # Verify no specific class, or empty list if that's the default
        assert isinstance(data[0].get("classNames"), list)

    def test_task_api_events_css_classes(self, client, user):
        client.force_login(user)
        base_date = "2025-01-15"
        Task.objects.create(
            title="Critical",
            due_date=base_date,
            priority=Task.Priority.CRITICAL,
            assigned_to=user,
        )
        Task.objects.create(
            title="Done", due_date=base_date, status=Task.Status.DONE, assigned_to=user
        )

        url = reverse("tasks:api-events")
        response = client.get(url, {"start": "2025-01-01", "end": "2025-01-31"})
        data = response.json()

        classes = {t["title"]: t["classNames"] for t in data}

        assert "fc-event-critical" in classes["Critical"]
        assert "fc-event-done" in classes["Done"]

    def test_task_list_filters(self, client, user):
        client.force_login(user)

        t1 = Task.objects.create(
            title="My Task", assigned_to=user, due_date="2025-01-01"
        )
        t2 = Task.objects.create(
            title="Unassigned Task", assigned_to=None, due_date="2025-01-01"
        )
        t3 = Task.objects.create(
            title="Done Task", status=Task.Status.DONE, due_date="2025-01-01"
        )

        # Test My Tasks
        url = reverse("tasks:list")
        response = client.get(url, {"mode": "my_tasks"})
        assert t1 in response.context["tasks"]
        assert t2 not in response.context["tasks"]

        # Test Status Filter
        response = client.get(url, {"status": "DONE"})
        assert t3 in response.context["tasks"]
        assert t1 not in response.context["tasks"]

    def test_calendar_view_context(self, client, user):
        client.force_login(user)
        url = reverse("tasks:calendar")
        response = client.get(url)
        assert response.status_code == 200
