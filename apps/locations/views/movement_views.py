from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView

from apps.base.views.mixins import CattleBulkActionMixin
from apps.locations.forms import MovementForm
from apps.locations.models import Movement
from apps.locations.services import MovementService


class MovementCreateView(LoginRequiredMixin, CattleBulkActionMixin, CreateView):

    model = Movement
    form_class = MovementForm
    template_name = "locations/movement_form.html"
    success_url = reverse_lazy("locations:list")

    # get_context_data and get_initial are handled by mixin

    def form_valid(self, form):
        # Use Service instead of standard form save
        cattle_list = self.get_valid_cattle_list(form)
        if not cattle_list:
            return self.form_invalid(form)

        try:
            MovementService.move_cattle(
                cattle_list=cattle_list,
                destination=form.cleaned_data["destination"],
                performed_by=self.request.user,
                reason=form.cleaned_data["reason"],
                move_date=form.cleaned_data.get("date"),
                notes=form.cleaned_data.get("notes", ""),
            )
            messages.success(self.request, _("Cattle moved successfully."))
        except ValidationError as e:
            # Handle ValidationErrors from Service
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        return redirect(self.success_url)

    def post(self, request, *args, **kwargs):
        # If 'destination' is not in POST, checks if this is the initial bulk action request
        if "destination" not in request.POST:
            # Treat as initial form load with data from POST
            return self.handle_initial_batch_post(request)

        return super().post(request, *args, **kwargs)
