from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.base.views.mixins import HandleProtectedErrorMixin
from apps.tasks.forms import TaskForm
from apps.tasks.models import Task
from apps.tasks.services.tasks import TaskService


class TaskCalendarView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/calendar.html"
    context_object_name = "tasks"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any initial context needed for the calendar
        return context


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    template_name = "tasks/task_list.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        search_query = self.request.GET.get("q")
        status = self.request.GET.get("status")
        priority = self.request.GET.get("priority")

        # "My Tasks" handling
        user = None
        if self.request.GET.get("mode") == "my_tasks":
            user = self.request.user

        return TaskService.get_all_tasks(
            search_query=search_query, status=status, priority=priority, user=user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_priority"] = self.request.GET.get("priority", "")
        context["status_choices"] = Task.Status.choices
        context["priority_choices"] = Task.Priority.choices
        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = "tasks/task_detail.html"

    def get_queryset(self):
        return super().get_queryset().select_related("content_type", "assigned_to")


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("tasks:calendar")


class TaskUpdateView(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = "tasks/task_form.html"
    success_url = reverse_lazy("tasks:calendar")


class TaskDeleteView(LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView):
    model = Task
    template_name = "tasks/task_confirm_delete.html"
    success_url = reverse_lazy("tasks:list")

    def delete(self, request, *args, **kwargs):
        # Default implementation or simple pass, logic moved to post
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            TaskService.delete_task(self.object)
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.get_success_url())
