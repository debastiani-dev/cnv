from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.cattle.models.cattle import Cattle
from apps.weight.models.session import WeighingSession
from apps.weight.services.weight_service import WeightService


class BatchWeighingView(LoginRequiredMixin, View):
    template_name = "weight/batch_entry.html"

    def get(self, request, pk):
        session = get_object_or_404(WeighingSession, pk=pk)

        # Get cattle IDs from session storage (passed from CreateView or List Action)
        # Alternatively, could pass as comma-separated query param if list is small.
        # Fallback: check query param 'ids'
        cattle_ids = request.session.get("batch_weighing_cattle_ids")

        if not cattle_ids:
            # Try query param
            ids_str = request.GET.get("ids")
            if ids_str:
                cattle_ids = ids_str.split(",")

        if not cattle_ids:
            messages.warning(request, _("No cattle selected for weighing."))
            return redirect("weight:session-detail", pk=pk)

        cattle_list = Cattle.objects.filter(pk__in=cattle_ids).order_by("tag")

        context = {
            "session": session,
            "cattle_list": cattle_list,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        session = get_object_or_404(WeighingSession, pk=pk)

        # Process the form data
        # Expecting inputs named "weight_{cattle_id}"

        cattle_ids = request.POST.getlist("cattle_ids")
        saved_count = 0
        errors = []

        for cattle_id in cattle_ids:
            weight_input = request.POST.get(f"weight_{cattle_id}")

            # Skip empty inputs (maybe didn't weigh this one)
            if not weight_input:
                continue

            try:
                weight_kg = Decimal(weight_input)
                if weight_kg < 0:
                    raise ValueError(_("Negative weight"))

                animal = Cattle.objects.get(pk=cattle_id)
                WeightService.record_weight(session, animal, weight_kg)
                saved_count += 1

            except (InvalidOperation, ValueError):
                errors.append(
                    f"Invalid weight for cattle ID {cattle_id}: {weight_input}"
                )
            except Cattle.DoesNotExist:
                errors.append(f"Cattle ID {cattle_id} not found")

        if errors:
            messages.warning(
                request, _("Some records had errors: ") + "; ".join(errors[:5])
            )

        if saved_count > 0:
            messages.success(
                request, _(f"Successfully recorded weights for {saved_count} animals.")
            )
        else:
            messages.info(request, _("No weights were recorded."))

        # Clear session storage
        if "batch_weighing_cattle_ids" in request.session:
            del request.session["batch_weighing_cattle_ids"]

        return redirect("weight:session-detail", pk=pk)
