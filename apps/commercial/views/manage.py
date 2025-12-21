from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView, DetailView, UpdateView

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.commercial.models import SalesEvent, SalesLot
from apps.commercial.services.commercial_service import CommercialService
from apps.partners.models import Partner

MANAGE_LOTS_URL_NAME = "commercial:manage_lots"


class ManageLotsView(LoginRequiredMixin, DetailView):
    model = SalesEvent
    template_name = "events/manage_lots.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filter out animals that are already assigned to a lot for this event.
        # Note: Animals are only marked as SOLD when the lot is closed, so we check existence in lots.

        existing_lot_animals = SalesLot.objects.filter(event=self.object).values_list(
            "animals", flat=True
        )

        context["available_animals"] = Cattle.objects.filter(
            status=Cattle.STATUS_AVAILABLE
        ).exclude(pk__in=existing_lot_animals)

        context["lots"] = self.object.lots.all().order_by("lot_number")

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Basic manual form handling for simplicity
        lot_number = request.POST.get("lot_number")
        reserve_price = request.POST.get("reserve_price")
        animal_ids = request.POST.getlist("animals")  # Expecting 'animals' input list

        if lot_number and reserve_price and animal_ids:
            # Create Lot
            # Calculate cost
            animals = Cattle.objects.filter(pk__in=animal_ids)
            # Use Money for currency calculations
            total_cost = Money(sum(a.total_cost for a in animals))
            reserve_price = Money(reserve_price)

            lot = SalesLot.objects.create(
                event=self.object,
                lot_number=lot_number,
                reserve_price=reserve_price,
                cost_at_creation=total_cost,
                status=SalesLot.STATUS_AVAILABLE,
            )
            lot.animals.set(animals)

            messages.success(
                request,
                f"Lot {lot.lot_number} created with {lot.animals.count()} animals.",
            )
            return self.get(request, *args, **kwargs)

        messages.error(request, "Please provide Lot Number, Price and select Animals.")
        return self.get(request, *args, **kwargs)


class SalesLotUpdateView(LoginRequiredMixin, UpdateView):
    model = SalesLot
    fields = ["lot_number", "reserve_price"]
    template_name = "events/lot_form.html"
    context_object_name = "lot"

    def get_success_url(self):
        messages.success(self.request, "Lot updated successfully.")
        return reverse_lazy(MANAGE_LOTS_URL_NAME, kwargs={"pk": self.object.event.pk})


class SalesLotDeleteView(LoginRequiredMixin, DeleteView):
    model = SalesLot
    template_name = "events/lot_confirm_delete.html"
    context_object_name = "lot"

    def get_success_url(self):
        event_pk = self.object.event.pk
        messages.success(
            self.request, "Lot deleted successfully. Animals are now available."
        )
        return reverse_lazy(MANAGE_LOTS_URL_NAME, kwargs={"pk": event_pk})


class CloseLotView(LoginRequiredMixin, UpdateView):
    model = SalesLot
    fields = []  # We handle form fields manually in post or via a custom template form
    template_name = "events/close_lot.html"
    context_object_name = "lot"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # We need a list of buyers (Partners)
        context["buyers"] = Partner.objects.all().order_by("name")
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        buyer_id = request.POST.get("buyer")
        hammer_price = request.POST.get("hammer_price")

        if buyer_id and hammer_price:
            try:
                buyer = Partner.objects.get(pk=buyer_id)
                price = Money(hammer_price)

                # Execute the Business Logic (The Bridge)
                CommercialService.close_lot(
                    lot=self.object,
                    buyer_partner=buyer,
                    final_hammer_price=price,
                    date=timezone.now().date(),
                )

                messages.success(request, f"Lot sold to {buyer.name} for {price}!")
                return HttpResponseRedirect(self.get_success_url())

            except Exception as e:  # pylint: disable=broad-exception-caught
                messages.error(request, f"Error closing lot: {e}")
                return self.get(request, *args, **kwargs)

        messages.error(
            request, "Please select a Buyer and enter the Final Hammer Price."
        )
        return self.get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(MANAGE_LOTS_URL_NAME, kwargs={"pk": self.object.event.pk})
