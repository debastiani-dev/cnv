from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.base.models.base_model import BaseModel


class SalesEvent(BaseModel):
    TYPE_AUCTION = "AUCTION"
    TYPE_DIRECT = "DIRECT"
    TYPE_SEMEN = "SEMEN"

    TYPE_CHOICES = [
        (TYPE_AUCTION, _("Auction")),
        (TYPE_DIRECT, _("Direct Sale")),
        (TYPE_SEMEN, _("Semen/Genetics")),
    ]

    name = models.CharField(_("Event Name"), max_length=100)
    date = models.DateField(_("Date"))
    sales_type = models.CharField(_("Type"), max_length=20, choices=TYPE_CHOICES)
    is_active = models.BooleanField(_("Active"), default=True)
    description = models.TextField(_("Description"), blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Sales Event")
        verbose_name_plural = _("Sales Events")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.name} ({self.date})"
