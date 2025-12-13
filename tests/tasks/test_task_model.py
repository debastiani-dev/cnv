# pylint: disable=unused-argument
import pytest
from django.utils import timezone

from apps.tasks.models import Task, TaskTemplate


@pytest.mark.django_db
class TestTaskModel:
    def test_create_task(self, user):
        task = Task.objects.create(
            title="Test Task",
            description="Test Description",
            due_date=timezone.now().date(),
            priority=Task.Priority.HIGH,
            assigned_to=user,
        )
        assert task.pk is not None
        assert task.status == Task.Status.PENDING
        assert str(task) == "Test Task (Pending)"

    def test_create_task_with_generic_relation(self, user, cattle):
        task = Task.objects.create(
            title="Cattle Task", due_date=timezone.now().date(), content_object=cattle
        )
        assert task.content_object == cattle
        assert task.content_type.model == "cattle"


@pytest.mark.django_db
class TestTaskTemplateModel:
    def test_create_template(self):
        template = TaskTemplate.objects.create(name="Protocol A", offset_days=7)
        assert template.pk is not None
        assert str(template) == "Protocol A"
