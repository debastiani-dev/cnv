from .api import TaskEventsView
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
    "TaskPermanentDeleteView",
    "TaskRestoreView",
    "TaskTrashListView",
]
