from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, ListView

from apps.nutrition.forms import FeedingEventForm
from apps.nutrition.models.event import FeedingEvent
from apps.nutrition.services.feeding_service import FeedingService


class FeedingEventListView(ListView):
    model = FeedingEvent
    template_name = "nutrition/event_list.html"
    context_object_name = "events"
    paginate_by = 20
    ordering = ["-date", "-created_at"]


class FeedingEventCreateView(CreateView):
    model = FeedingEvent
    form_class = FeedingEventForm
    template_name = "nutrition/event_form.html"
    success_url = reverse_lazy("nutrition:event-list")

    def form_valid(self, form):
        # Override to avoid double save and catch service errors
        try:
            FeedingService.record_feeding(
                location=form.cleaned_data["location"],
                diet=form.cleaned_data["diet"],
                amount_kg=form.cleaned_data["amount_kg"],
                date=form.cleaned_data["date"],
                performed_by=self.request.user,
            )
            messages.success(self.request, _("Feeding event recorded successfully."))
            return HttpResponseRedirect(self.success_url)

        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
