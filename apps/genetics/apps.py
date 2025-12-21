from django.apps import AppConfig


class GeneticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.genetics"

    def ready(self):
        import apps.genetics.signals  # noqa: F401 #pylint: disable=import-outside-toplevel, unused-import
