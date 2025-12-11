from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView

from apps.cattle.models import Cattle
from apps.locations.forms import MovementForm
from apps.locations.models import Movement
from apps.locations.services import MovementService


class MovementCreateView(LoginRequiredMixin, CreateView):
    model = Movement
    form_class = MovementForm
    template_name = "locations/movement_form.html"
    success_url = reverse_lazy("locations:list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass cattle list for display
        cattle_ids = self._get_cattle_ids()
        if cattle_ids:
            context["cattle_list"] = Cattle.objects.filter(pk__in=cattle_ids)
        return context

    def get_initial(self):
        initial = super().get_initial()
        cattle_ids = self._get_cattle_ids()
        if cattle_ids:
            initial["cattle_ids"] = ",".join(cattle_ids)
        return initial

    def form_valid(self, form):
        # Use Service instead of standard form save
        cattle_ids_str = form.cleaned_data.get("cattle_ids")
        if not cattle_ids_str:
            messages.error(self.request, _("No cattle selected."))
            return self.form_invalid(form)

        cattle_ids = cattle_ids_str.split(",")
        cattle_list = list(Cattle.objects.filter(pk__in=cattle_ids))

        if not cattle_list:
            messages.error(self.request, _("Invalid cattle selection."))
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
            cattle_ids = self._get_cattle_ids()
            if not cattle_ids:
                messages.error(request, _("No cattle selected."))
                return redirect("cattle:list")

            # Initialize form with the cattle IDs
            form = self.form_class(initial={"cattle_ids": ",".join(cattle_ids)})
            self.object = None
            return self.render_to_response(self.get_context_data(form=form))

        return super().post(request, *args, **kwargs)

    def _get_cattle_ids(self):
        # 1. Try GET list
        ids_list = self.request.GET.getlist("cattle_ids")
        if ids_list:
            return ids_list

        # 2. Try POST list
        ids_list = self.request.POST.getlist("cattle_ids")

        # If list has > 1 item, it's definitely multiple checkboxes
        if len(ids_list) > 1:
            return ids_list

        # If list has 1 item, it could be a single checkbox ("id1") OR a hidden field ("id1,id2")
        if len(ids_list) == 1:
            val = ids_list[0]
            if "," in val:
                return val.split(",")
            return [val]

        return []
