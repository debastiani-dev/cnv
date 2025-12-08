from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel


class Partner(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    tax_id = models.CharField(
        _("Tax ID"), max_length=50, blank=True, help_text=_("CPF/CNPJ")
    )

    email = models.EmailField(_("Email"), blank=True)
    phone = models.CharField(_("Phone"), max_length=20, blank=True)

    is_customer = models.BooleanField(_("Customer"), default=True)
    is_supplier = models.BooleanField(_("Supplier"), default=False)

    notes = models.TextField(_("Notes"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Partner")
        verbose_name_plural = _("Partners")

    def __str__(self):
        return self.name
