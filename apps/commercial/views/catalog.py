from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

from apps.commercial.models import SalesEvent, SalesLot


class LotPrintView(DetailView):
    model = SalesLot
    template_name = "catalog/print_view.html"
    context_object_name = "lot"


class EventCatalogView(LoginRequiredMixin, DetailView):
    model = SalesEvent
    template_name = "catalog/event_catalog.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prefetch lots and their animals for efficiency
        context["lots"] = self.object.lots.prefetch_related("animals").all()
        return context
