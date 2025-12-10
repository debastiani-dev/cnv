from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReproductionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reproduction"
    verbose_name = _("Reproduction")
