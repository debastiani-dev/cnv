from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView, View

from apps.commercial.models import SalesEvent

EVENT_LIST_URL_NAME = "commercial:event_list"


class SalesEventListView(LoginRequiredMixin, ListView):
    model = SalesEvent
    template_name = "events/event_list.html"
    context_object_name = "events"
    paginate_by = 10

    def get_queryset(self):
        queryset = SalesEvent.objects.annotate(lots_count=Count("lots"))

        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )

        date_after = self.request.GET.get("date_after")
        if date_after:
            queryset = queryset.filter(date__gte=date_after)

        date_before = self.request.GET.get("date_before")
        if date_before:
            queryset = queryset.filter(date__lte=date_before)

        return queryset.order_by("-date")


class SalesEventCreateView(LoginRequiredMixin, CreateView):
    model = SalesEvent
    fields = ["name", "date", "sales_type", "description"]
    template_name = "events/event_form.html"
    success_url = reverse_lazy(EVENT_LIST_URL_NAME)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Sales Event"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Event created successfully.")
        return super().form_valid(form)


class SalesEventUpdateView(LoginRequiredMixin, UpdateView):
    model = SalesEvent
    fields = ["name", "date", "sales_type", "description"]
    template_name = "events/event_form.html"
    success_url = reverse_lazy(EVENT_LIST_URL_NAME)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Sales Event"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Event updated successfully.")
        return super().form_valid(form)


class SalesEventDeleteView(LoginRequiredMixin, DeleteView):
    model = SalesEvent
    template_name = "events/event_confirm_delete.html"
    success_url = reverse_lazy(EVENT_LIST_URL_NAME)

    def form_valid(self, form):
        self.object.soft_delete()  # Explicitly using soft_delete from BaseModel
        messages.success(self.request, "Event moved to trash.")
        return HttpResponseRedirect(self.success_url)


class SalesEventTrashView(LoginRequiredMixin, ListView):
    model = SalesEvent
    template_name = "events/event_trash_list.html"
    context_object_name = "events"
    paginate_by = 10

    def get_queryset(self):
        return SalesEvent.all_objects.filter(is_deleted=True)


class SalesEventRestoreView(LoginRequiredMixin, UpdateView):
    model = SalesEvent
    fields = []
    template_name = "events/event_confirm_restore.html"
    success_url = reverse_lazy("commercial:event_trash")

    def get_queryset(self):
        return SalesEvent.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        self.object.restore()
        messages.success(self.request, "Event restored successfully.")
        return super().form_valid(form)


class SalesEventHardDeleteView(LoginRequiredMixin, DeleteView):
    model = SalesEvent
    template_name = "events/event_confirm_permanent_delete.html"
    success_url = reverse_lazy("commercial:event_trash")

    def get_queryset(self):
        return SalesEvent.all_objects.filter(is_deleted=True)

    def form_valid(self, form):
        self.object.delete(destroy=True)
        messages.success(self.request, "Event permanently deleted.")
        return HttpResponseRedirect(self.success_url)


class SalesEventToggleActiveView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        try:
            event = SalesEvent.objects.get(pk=pk)
            event.is_active = not event.is_active
            event.save()
            return JsonResponse({"status": "success", "is_active": event.is_active})
        except SalesEvent.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Event not found"}, status=404
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
