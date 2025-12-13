from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tasks"

    def ready(self):
        # Pylint false positive
        # pylint: disable=import-outside-toplevel, unused-import
        import apps.tasks.signals  # noqa: F401
