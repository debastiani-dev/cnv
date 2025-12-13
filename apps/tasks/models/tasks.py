from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel


class TaskTemplate(BaseModel):
    """
    Standard Operating Procedures (SOP) for recurring protocols.
    """

    name = models.CharField(_("Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    offset_days = models.PositiveIntegerField(
        _("Offset Days"),
        default=0,
        help_text=_("Days after the trigger event to due date."),
    )

    class Meta:
        verbose_name = _("Task Template")
        verbose_name_plural = _("Task Templates")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Task(BaseModel):
    """
    Represents an actionable task assigned to a user or generic.
    """

    class Priority(models.TextChoices):
        LOW = "LOW", _("Low")
        MEDIUM = "MEDIUM", _("Medium")
        HIGH = "HIGH", _("High")
        CRITICAL = "CRITICAL", _("Critical")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        DONE = "DONE", _("Done")
        CANCELED = "CANCELED", _("Canceled")

    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    due_date = models.DateField(_("Due Date"))

    priority = models.CharField(
        _("Priority"),
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name=_("Assigned To"),
    )

    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)

    # Context / Link to other objects (Cow, Paddock, etc)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Content Type"),
    )
    object_id = models.UUIDField(_("Object ID"), null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    task_template = models.ForeignKey(
        TaskTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        verbose_name=_("Template Source"),
    )

    class Meta:
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ["due_date", "-priority"]
        indexes = [
            models.Index(fields=["due_date", "status"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
