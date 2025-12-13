# pylint: disable=unused-argument
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.health.models import Medication, MedicationType, SanitaryEvent
from apps.reproduction.models import BreedingEvent, PregnancyCheck
from apps.tasks.models import Task, TaskTemplate
from apps.tasks.services.tasks import TaskService


@pytest.mark.django_db
class TestTaskService:
    def test_create_task_from_trigger(self, cattle):
        today = timezone.now().date()
        task = TaskService.create_task_from_trigger(
            title="Triggered Task",
            description="Auto generated",
            due_date=today,
            content_object=cattle,
        )
        assert task is not None
        assert task.content_object == cattle

        # Test duplicate prevention
        duplicate = TaskService.create_task_from_trigger(
            title="Triggered Task",
            description="Auto generated",
            due_date=today,
            content_object=cattle,
        )
        assert duplicate is None

    def test_create_task_with_template(self, cattle):
        today = timezone.now().date()
        template = TaskTemplate.objects.create(
            name="Protocol X", offset_days=5, description="Template Description"
        )

        task = TaskService.create_task_from_trigger(
            title="Templated Task",
            description="",  # Should fallback to template
            due_date=today,
            content_object=cattle,
            template=template,
        )

        assert task.description == "Template Description"
        assert task.due_date == today + timedelta(days=5)

    def test_get_overdue_tasks(self, user):
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        # Overdue task
        t1 = Task.objects.create(title="Overdue", due_date=yesterday, assigned_to=user)
        # Future task
        t2 = Task.objects.create(title="Future", due_date=today, assigned_to=user)
        # Done task (even if overdue date)
        t3 = Task.objects.create(
            title="Done Overdue",
            due_date=yesterday,
            status=Task.Status.DONE,
            assigned_to=user,
        )

        overdue = TaskService.get_overdue_tasks(user)
        assert t1 in overdue
        assert t2 not in overdue
        assert t3 not in overdue

    def test_breeding_trigger(self, cattle, bull):
        # Create BreedingEvent
        breeding = BreedingEvent.objects.create(
            dam=cattle,
            sire=bull,
            date=timezone.now().date(),
            breeding_method=BreedingEvent.METHOD_NATURAL,
        )

        # Signal should have fired
        task = Task.objects.filter(
            content_type__model="cattle",
            object_id=cattle.pk,
            title="Pregnancy Diagnosis",
        ).first()

        assert task is not None
        expected_date = breeding.date + timedelta(days=30)
        assert task.due_date == expected_date

    def test_pregnancy_trigger(self, cattle, bull):
        breeding = BreedingEvent.objects.create(
            dam=cattle,
            sire=bull,
            date=timezone.now().date(),
            breeding_method=BreedingEvent.METHOD_NATURAL,
        )
        # Clear any tasks from breeding trigger
        Task.objects.all().delete()

        # Create Positive PregnancyCheck
        PregnancyCheck.objects.create(
            date=timezone.now().date(),
            result=PregnancyCheck.RESULT_POSITIVE,
            breeding_event=breeding,
        )

        task = Task.objects.filter(
            content_type__model="cattle", object_id=cattle.pk, title="Move to Maternity"
        ).first()

        assert task is not None
        # Logic: due_date = expected_calving - 7 days.
        # expected_calving is roughly breeding date + 283 days.
        expected_calving = breeding.date + timedelta(days=283)
        expected_due = expected_calving - timedelta(days=7)
        assert task.due_date == expected_due

    def test_sanitary_trigger(self, cattle):
        # Since logic isn't fully implemented, we verify it exists or passes gently
        # Or we implement the logic for "Booster" check in test if we mocked it.
        # Currently the service implementation passed. So no task should be created unless we fix logic.

        med = Medication.objects.create(
            name="Vac", medication_type=MedicationType.VACCINE
        )
        event = SanitaryEvent.objects.create(
            date=timezone.now().date(), title="Vaccination A", medication=med
        )
        # Since implementation is now checking for VACCINE type, a task SHOULD be created
        task = Task.objects.filter(title__startswith="Booster:").first()
        assert task is not None
        assert task.content_object == event
        assert task.due_date == event.date + timedelta(days=21)
