from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.views import View

from apps.tasks.models import Task


class TaskEventsView(LoginRequiredMixin, View):
    """
    API endpoint to return tasks as JSON events for FullCalendar.
    """

    def get(self, request, *args, **kwargs):
        start_date = request.GET.get("start")
        end_date = request.GET.get("end")

        # Ensure we have clean dates (FullCalendar might send ISO with time)
        if start_date:
            start_date = start_date.split("T")[0]
        if end_date:
            end_date = end_date.split("T")[0]

        # If no range provided, fail gracefully or default (though FC always sends it)
        if not start_date or not end_date:
            return JsonResponse([], safe=False)

        tasks = (
            Task.objects.select_related("assigned_to", "content_type")
            .filter(due_date__range=[start_date, end_date])
            .exclude(status=Task.Status.CANCELED)
        )

        mode = request.GET.get("mode")
        print(f"DEBUG: mode={mode}, user={request.user}, GET={request.GET}")
        if mode == "my_tasks":
            tasks = tasks.filter(assigned_to=request.user)

        events = []
        for task in tasks:
            # Map Priority/Status to classNames
            class_names = []
            if task.priority == Task.Priority.CRITICAL:
                class_names.append("fc-event-critical")
            elif task.status == Task.Status.DONE:
                class_names.append("fc-event-done")

            # Build event title with linked object
            event_title = task.title
            if task.content_object:
                linked_type = (
                    task.content_type.name.title() if task.content_type else "Unknown"
                )
                event_title = f"{task.title} [{linked_type}: {task.content_object}]"

            # Build linked object info for tooltip
            linked_info = None
            if task.content_object:
                linked_type = (
                    task.content_type.name.title() if task.content_type else "Unknown"
                )
                linked_info = f"{linked_type}: {task.content_object}"

            events.append(
                {
                    "id": task.pk,
                    "title": event_title,
                    "start": task.due_date.isoformat(),
                    "classNames": class_names,
                    "url": reverse("tasks:detail", args=[task.pk]),
                    "extendedProps": {
                        "description": task.description,
                        "priority": task.priority,
                        "status": task.get_status_display(),
                        "assigned_to": (
                            task.assigned_to.get_full_name()
                            if task.assigned_to
                            else "Unassigned"
                        ),
                        "linked_to": linked_info,
                    },
                }
            )

        return JsonResponse(events, safe=False)
