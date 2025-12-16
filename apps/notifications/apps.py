from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    label = "notifications"
    verbose_name = _("Notifications")

    def ready(self):
        # pylint: disable=import-outside-toplevel, unused-import
        import apps.notifications.services.listeners  # noqa: F401
