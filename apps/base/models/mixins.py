from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.authentication.models.user import User


class PerformedByMixin(models.Model):
    """
    Abstract mixin for models that track who performed the action.
    """

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_performed",
        verbose_name=_("Performed By"),
    )

    class Meta:
        abstract = True
