from .api import TaskEventsView, TaskStatusUpdateView
from .tasks import (
    TaskCalendarView,
    TaskCreateView,
    TaskDeleteView,
    TaskDetailView,
    TaskListView,
    TaskUpdateView,
)
from .trash import TaskPermanentDeleteView, TaskRestoreView, TaskTrashListView

__all__ = [
    "TaskCalendarView",
    "TaskCreateView",
    "TaskDeleteView",
    "TaskDetailView",
    "TaskListView",
    "TaskUpdateView",
    "TaskEventsView",
    "TaskStatusUpdateView",
    "TaskPermanentDeleteView",
    "TaskRestoreView",
    "TaskTrashListView",
]
