from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WeightConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.weight"
    verbose_name = _("Weight & Performance")
