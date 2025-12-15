import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
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


class TaskStatusUpdateView(LoginRequiredMixin, View):
    """
    API endpoint to update task status via JSON.
    """

    def post(self, request, pk, *args, **kwargs):
        try:
            data = json.loads(request.body)
            new_status = data.get("status")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        task = get_object_or_404(Task, pk=pk)

        # Permission check: User must own the task or be assigned to it?
        # Requirement: "Fetch Task by UUID (ensure user has permission)."
        # Assuming typical rules: owner/assigned or superuser.
        # For now, simplistic check: if user can view it (LoginRequired), they might be able to edit.
        # But let's restrict to assigned_to or maybe verify against a permission policy.
        # Given "My Tasks" context, allow if assigned_to == user or user has generic change_task perm.
        if (
            task.assigned_to
            and task.assigned_to != request.user
            and not request.user.has_perm("tasks.change_task")
        ):
            return JsonResponse({"error": "Permission denied"}, status=403)

        if new_status not in Task.Status.values:
            return JsonResponse({"error": "Invalid status code"}, status=400)

        task.status = new_status
        if new_status == Task.Status.DONE:
            task.completed_at = timezone.now()
        else:
            # clear completed_at if moving back from DONE? Requirement didn't specify, but logical.
            task.completed_at = None

        task.save()

        # Helper to get color class - minimal logic derived from template logic
        # You might want to centralize this in the model method `get_status_color_class`
        # Assuming the model has `get_status_color_class` or we define it here or on frontend.
        # Template requirement used `{{ task.get_status_color_class }}`.
        # We need to return this class string.
        # I'll check if the model has this method or if it was a template tag/property.
        # If not in model, I'll add the property to the model too or approximate it.
        # For now, let's verify if `get_status_color_class` exists on model.
        # Warning: I didn't see it in the `view_file` output above!
        # I will inject a simplified map here for response.

        status_colors = {
            "PENDING": "bg-yellow-50 text-yellow-800 ring-yellow-600/20",
            "IN_PROGRESS": "bg-blue-50 text-blue-700 ring-blue-700/10",
            "DONE": "bg-green-50 text-green-700 ring-green-600/20",
            "CANCELED": "bg-gray-50 text-gray-600 ring-gray-500/10",
        }
        color_class = status_colors.get(new_status, "bg-gray-50 text-gray-600")

        return JsonResponse(
            {
                "success": True,
                "new_status_display": task.get_status_display(),
                "color_class": color_class,
            }
        )
