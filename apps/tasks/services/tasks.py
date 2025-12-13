from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from apps.tasks.models import Task


class TaskService:
    @staticmethod
    def create_task_from_trigger(
        title,
        description,
        due_date,
        content_object,
        priority=Task.Priority.MEDIUM,
        template=None,
    ):
        """
        Generic method to create a task from a trigger event.
        """
        # Avoid duplication: Check if similar active task exists
        content_type = ContentType.objects.get_for_model(content_object)
        existing = Task.objects.filter(
            content_type=content_type,
            object_id=content_object.pk,
            title=title,
            status__in=[Task.Status.PENDING, Task.Status.IN_PROGRESS],
        ).exists()

        if existing:
            return None

        # Apply template offset if provided
        if template:
            due_date = due_date + timedelta(days=template.offset_days)
            if not description and template.description:
                description = template.description

        task = Task.objects.create(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            content_object=content_object,
            task_template=template,
        )
        return task

    @staticmethod
    def get_all_tasks(search_query=None, status=None, priority=None, user=None):
        """
        Returns filtered tasks.
        search_query: string to search in title/description
        status: single status string or list of status strings
        priority: priority string
        user: filter by assigned_to user
        """

        queryset = (
            Task.objects.select_related("content_type", "assigned_to")
            .all()
            .order_by("due_date", "-priority")
        )

        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
            )

        if status:
            if isinstance(status, (list, tuple)):
                queryset = queryset.filter(status__in=status)
            else:
                queryset = queryset.filter(status=status)

        if priority:
            queryset = queryset.filter(priority=priority)

        if user:
            queryset = queryset.filter(assigned_to=user)

        return queryset

    @staticmethod
    def get_overdue_tasks(user=None):
        """
        Returns tasks where due_date < today AND status != DONE.
        Optional: filter by assigned user.
        """
        today = timezone.localdate()
        return (
            TaskService.get_all_tasks(
                status=None, user=user  # handled below by exclusion
            )
            .filter(due_date__lt=today)
            .exclude(status__in=[Task.Status.DONE, Task.Status.CANCELED])
        )

    # --- Domain Specific Triggers ---

    @staticmethod
    def handle_breeding_event(breeding_event):
        """
        Triggered when a BreedingEvent is saved.
        Action: Create Task "Pregnancy Diagnosis" linked to Cow, Due Date = event.date + 30 days.
        """
        # Cow is the dam
        cow = breeding_event.dam
        due_date = breeding_event.date + timedelta(days=30)

        TaskService.create_task_from_trigger(
            title="Pregnancy Diagnosis",
            description=f"Check for pregnancy after breeding on {breeding_event.date}",
            due_date=due_date,
            content_object=cow,
            priority=Task.Priority.HIGH,
        )

    @staticmethod
    def handle_pregnancy_check(pregnancy_check):
        """
        Triggered when a PregnancyCheck (Positive) is saved.
        Action: Create Task "Move to Maternity" linked to Cow, Due Date = expected_calving - 7 days.
        """
        if pregnancy_check.is_pregnant:
            # Task 1: "Move to Maternity" - 7 days before expected calving
            # Logic: expected_calving_date should be on PregnancyCheck model
            expected_calving = pregnancy_check.expected_calving_date

            if not expected_calving and pregnancy_check.breeding_event:
                # Fallback: Estimate based on breeding date + 283 days (Gestation Period)
                expected_calving = pregnancy_check.breeding_event.date + timedelta(
                    days=283
                )

            if expected_calving:
                TaskService.create_task_from_trigger(
                    title="Move to Maternity",
                    description=f"Move {pregnancy_check.breeding_event.dam.tag} to maternity paddock.",
                    due_date=expected_calving - timedelta(days=7),
                    content_object=pregnancy_check.breeding_event.dam,
                    priority=Task.Priority.HIGH,
                )

    @staticmethod
    def handle_sanitary_event(sanitary_event):
        """
        Triggered when a SanitaryEvent is saved.
        Action: If vaccine (by name/type) implies booster, Create Task "Booster Shot", Due Date = event.date + 21 days.
        """
        # Heuristic: If "Vaccine" type and title contains "Booster" or Generic trigger
        # For MVP: If medication type is VACCINE, trigger Booster reminder.
        if (
            sanitary_event.medication
            and sanitary_event.medication.medication_type == "VACCINE"
        ):
            due_date = sanitary_event.date + timedelta(days=21)

            # Link to first target animal if exists, or just valid task without link?
            # If multiple targets, maybe one task per animal? Or one general task?
            # For now, let's create a General Task linked to the event itself (since generic relation supports any model)

            TaskService.create_task_from_trigger(
                title=f"Booster: {sanitary_event.title}",
                description=f"Booster shot required for {sanitary_event.title}",
                due_date=due_date,
                content_object=sanitary_event,  # Link to the Event itself
                priority=Task.Priority.HIGH,
            )

    @staticmethod
    def delete_task(task):
        """
        Soft delete a task.
        """
        task.delete()

    @staticmethod
    def restore_task(pk):
        """
        Restore a soft-deleted task.
        """
        task = Task.all_objects.get(pk=pk)
        task.restore()
        return task

    @staticmethod
    def hard_delete_task(pk):
        """
        Permanently delete a task.
        """
        task = Task.all_objects.get(pk=pk)
        task.delete(destroy=True)

    @staticmethod
    def get_deleted_tasks():
        """
        Return a queryset of soft-deleted tasks.
        """
        return Task.all_objects.filter(is_deleted=True)
