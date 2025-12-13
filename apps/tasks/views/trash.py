from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView

from apps.base.views.mixins import HandleProtectedErrorMixin
from apps.tasks.models import Task
from apps.tasks.services.tasks import TaskService


class TaskTrashListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/task_trash_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        return TaskService.get_deleted_tasks()


class TaskRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            TaskService.restore_task(pk)
            messages.success(request, _("Task restored successfully."))
        except ValueError as e:
            messages.error(request, str(e))
        except Task.DoesNotExist:
            messages.error(request, _("Task not found."))

        return HttpResponseRedirect(reverse_lazy("tasks:list"))

    def get(self, request, pk):
        try:
            task = Task.all_objects.get(pk=pk)
            return render(request, "tasks/task_confirm_restore.html", {"task": task})
        except Task.DoesNotExist:
            messages.error(request, _("Task not found."))
            return HttpResponseRedirect(reverse_lazy("tasks:list"))


class TaskPermanentDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, View):
    def post(self, request, pk):
        try:
            TaskService.hard_delete_task(pk)
            messages.success(request, _("Task permanently deleted."))
        except Task.DoesNotExist:
            messages.error(request, _("Task not found."))
        except (ValidationError, ProtectedError) as e:
            task = Task.all_objects.get(pk=pk)
            self.object = task
            return self.handle_delete_error(
                request,
                e,
                template_name="tasks/task_confirm_permanent_delete.html",
                context_object_name="task",
            )

        return HttpResponseRedirect(reverse_lazy("tasks:trash"))

    def get(self, request, pk):
        try:
            task = Task.all_objects.get(pk=pk)
            return render(
                request,
                "tasks/task_confirm_permanent_delete.html",
                {"task": task},
            )
        except Task.DoesNotExist:
            messages.error(request, _("Task not found."))
            return HttpResponseRedirect(reverse_lazy("tasks:trash"))
