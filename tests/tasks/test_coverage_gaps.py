# pylint: disable=unused-argument
import pytest
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.tasks.forms import TaskForm
from apps.tasks.models import Task
from apps.tasks.services.tasks import TaskService


@pytest.mark.django_db
class TestTaskCoverageGaps:

    # --- TaskForm Coverage ---
    def test_task_form_clean_object_id_none(self):
        """Test that empty string object_id is converted to None."""
        # We don't care if it's valid overall (missing assigned_to etc),
        # just want to check clean_object_id logic if we can invoke it,
        # OR verify full save with empty object_id works

        # Let's try full clean with valid data
        user = baker.make("authentication.User")
        form = TaskForm(
            data={
                "title": "Test",
                "description": "",
                "due_date": "2025-01-01",
                "priority": Task.Priority.MEDIUM,
                "status": Task.Status.PENDING,
                "assigned_to": user.pk,
                "object_id": "",
            }
        )
        assert form.is_valid()
        assert form.cleaned_data["object_id"] is None

    def test_task_form_clean_object_id_value(self):
        """Test that valid UUID string object_id is returned as is."""
        valid_uuid = "12345678-1234-5678-1234-567812345678"
        # Since we just want to test clean_object_id, we can mock or just use valid data for that field
        form = TaskForm(
            data={
                "title": "Test",
                "due_date": "2025-01-01",
                "priority": Task.Priority.MEDIUM,
                "status": Task.Status.PENDING,
                "object_id": valid_uuid,
            }
        )
        # It might not be fully valid if assigned_to is missing, but clean_object_id runs before full validation
        # Accessing cleaned_data requires full_clean.
        # Using Is Valid (ignoring errors other than object_id) is easier.
        form.full_clean()
        # We expect object_id to be in cleaned_data if it passed its own validation
        assert form.cleaned_data.get("object_id") == valid_uuid

    # --- TaskService Coverage ---
    def test_get_all_tasks_filters(self, user):
        t1 = Task.objects.create(
            title="Alpha",
            description="First task",
            priority=Task.Priority.HIGH,
            assigned_to=user,
            due_date="2025-01-01",
        )
        t2 = Task.objects.create(
            title="Beta",
            description="Second task",
            priority=Task.Priority.LOW,
            due_date="2025-01-01",
        )
        t3 = Task.objects.create(
            title="Gamma",
            description="Third task",
            status=Task.Status.DONE,
            due_date="2025-01-01",
        )

        # Search Query (Title)
        qs = TaskService.get_all_tasks(search_query="Alpha")
        assert t1 in qs
        assert t2 not in qs

        # Search Query (Description)
        qs = TaskService.get_all_tasks(search_query="Second")
        assert t2 in qs
        assert t1 not in qs

        # Status List
        qs = TaskService.get_all_tasks(status=[Task.Status.PENDING])
        assert t1 in qs  # Default is pending
        assert t3 not in qs

        # Priority
        qs = TaskService.get_all_tasks(priority=Task.Priority.LOW)
        assert t2 in qs
        assert t1 not in qs

    # --- TaskView API Coverage ---
    def test_api_events_missing_dates(self, client, user):
        client.force_login(user)
        url = reverse("tasks:api-events")
        response = client.get(url)  # No params
        assert response.status_code == 200
        assert response.json() == []

    def test_api_events_linked_object(self, client, user):
        client.force_login(user)
        cow = baker.make(Cattle, tag="COW-999")
        Task.objects.create(
            title="Vet Visit",
            due_date="2025-01-10",
            assigned_to=user,
            content_object=cow,
        )

        url = reverse("tasks:api-events")
        response = client.get(url, {"start": "2025-01-01", "end": "2025-01-31"})
        data = response.json()

        assert len(data) == 1
        # Check event title contains linked object
        assert "Cattle: COW-999" in data[0]["title"]
        # Check extendedProps
        props = data[0]["extendedProps"]
        assert "Cattle: COW-999" in props["linked_to"]

    def test_api_events_my_tasks(self, client, user):
        """Test mode='my_tasks' filtering."""
        client.force_login(user)
        other_user = baker.make("authentication.User")

        Task.objects.create(title="My Task", due_date="2025-01-10", assigned_to=user)
        Task.objects.create(
            title="Other Task", due_date="2025-01-10", assigned_to=other_user
        )

        url = reverse("tasks:api-events")
        response = client.get(
            url, {"start": "2025-01-01", "end": "2025-01-31", "mode": "my_tasks"}
        )
        data = response.json()

        assert len(data) == 1
        assert data[0]["title"] == "My Task"

    # --- TaskDetailView Coverage ---
    def test_detail_view_select_related(self, client, user):
        """Verify DetailView loads and executes get_queryset."""
        client.force_login(user)
        task = Task.objects.create(
            title="Detail Task", assigned_to=user, due_date="2025-01-01"
        )
        url = reverse("tasks:detail", kwargs={"pk": task.pk})

        # We want to ensure select_related is called, which isn't easy to assert directly
        # without mocking or checking query counts, but running the view proves it doesn't crash.
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["task"] == task
