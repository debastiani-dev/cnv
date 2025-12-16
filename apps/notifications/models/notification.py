from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.authentication.models import User
from apps.base.models.base_model import BaseModel


class Notification(BaseModel):
    class Category(models.TextChoices):
        ALERT = "ALERT", _("Alert")
        REMINDER = "REMINDER", _("Reminder")
        INFO = "INFO", _("Info")
        SUCCESS = "SUCCESS", _("Success")

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    message = models.TextField(verbose_name=_("Message"))
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.INFO,
        verbose_name=_("Category"),
    )
    link = models.CharField(max_length=500, blank=True, verbose_name=_("Link"))
    is_read = models.BooleanField(default=False, verbose_name=_("Is Read"))

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category}: {self.title} ({self.recipient.username})"
