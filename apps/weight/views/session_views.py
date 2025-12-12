from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from apps.weight.forms import WeighingSessionForm
from apps.weight.models import WeighingSession, WeighingSessionType


class WeighingSessionListView(LoginRequiredMixin, ListView):
    model = WeighingSession
    template_name = "weight/session_list.html"
    context_object_name = "sessions"
    paginate_by = 20

    def get_queryset(self):
        queryset = WeighingSession.objects.all().order_by("-date")

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(notes__icontains=search_query)
                | Q(date__icontains=search_query)
            )

        type_filter = self.request.GET.get("type")
        if type_filter:
            queryset = queryset.filter(session_type=type_filter)

        # Date Range Filter
        date_after = self.request.GET.get("date_after")
        date_before = self.request.GET.get("date_before")
        if date_after:
            queryset = queryset.filter(date__gte=date_after)
        if date_before:
            queryset = queryset.filter(date__lte=date_before)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["type_choices"] = WeighingSessionType.choices
        context["selected_type"] = self.request.GET.get("type", "")
        # Preserve date params
        context["date_after"] = self.request.GET.get("date_after", "")
        context["date_before"] = self.request.GET.get("date_before", "")
        return context


class WeighingSessionCreateView(LoginRequiredMixin, CreateView):
    model = WeighingSession
    form_class = WeighingSessionForm
    template_name = "weight/session_form.html"

    def form_valid(self, form):
        form.instance.performed_by = self.request.user
        response = super().form_valid(form)
        # If we have selected cattle in session (via GET/POST param), we might redirect
        # to the batch entry view. checks for 'cattle_ids' in the request.
        cattle_ids = self.request.POST.getlist("cattle_ids")
        if not cattle_ids:
            cattle_ids = self.request.GET.getlist("cattle_ids")

        if cattle_ids:
            # Redirect to batch entry with these IDs
            # We need to pass them to the batch view, typically via URL or session?
            # URL limit is a concern for many IDs.
            # Storing in session is safer.
            self.request.session["batch_weighing_cattle_ids"] = cattle_ids
            return redirect("weight:batch-entry", pk=self.object.pk)

        return response

    def get_success_url(self):
        # Default success url if no cattle selected (just creating empty session)
        return reverse_lazy("weight:session-detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass cattle_ids back to form if present
        context["cattle_ids"] = self.request.GET.getlist(
            "cattle_ids"
        ) or self.request.POST.getlist("cattle_ids")
        return context


class WeighingSessionDetailView(LoginRequiredMixin, DetailView):
    model = WeighingSession
    template_name = "weight/session_detail.html"
    context_object_name = "session"
