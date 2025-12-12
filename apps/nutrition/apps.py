from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NutritionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.nutrition"
    verbose_name = _("Nutrição")
