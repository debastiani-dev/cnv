from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView

from apps.base.views.mixins import CattleBulkActionMixin
from apps.finance.forms import BatchCostForm
from apps.finance.models.finance import CostEntry
from apps.finance.services.costing import CostingService


class CostBatchCreateView(LoginRequiredMixin, CattleBulkActionMixin, CreateView):
    model = CostEntry
    form_class = BatchCostForm
    template_name = "finance/cost_batch_add.html"
    success_url = reverse_lazy("cattle:list")

    # get_context_data and get_initial are handled by mixin

    def form_valid(self, form):
        cattle_list = self.get_valid_cattle_list(form)
        if not cattle_list:
            return self.form_invalid(form)

        # Create costs
        CostingService.create_batch_costs(cattle_list, form.cleaned_data)

        messages.success(
            self.request,
            _("Successfully added costs for %(count)d animals.")
            % {"count": len(cattle_list)},
        )
        return redirect(self.success_url)

    def post(self, request, *args, **kwargs):
        # Implementation similar to MovementCreateView:
        # If 'amount' (a required field) is not in POST, checking if it's the initial call from list
        # However, checking a field that is unique to the "filled" form is safer.
        # "amount" is good.

        if "amount" not in request.POST:
            # Initial load via POST (button click in list)
            return self.handle_initial_batch_post(request)

        return super().post(request, *args, **kwargs)
