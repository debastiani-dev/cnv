from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DeleteView, ListView, UpdateView

from apps.base.views.mixins import HandleProtectedErrorMixin
from apps.weight.forms import WeighingSessionForm
from apps.weight.models import WeighingSession

SESSION_LIST_URL = "weight:session-list"
SESSION_NOT_FOUND_MSG = _("Session not found.")


class WeighingSessionUpdateView(LoginRequiredMixin, UpdateView):
    model = WeighingSession
    form_class = WeighingSessionForm
    template_name = "weight/session_form.html"
    success_url = reverse_lazy(SESSION_LIST_URL)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Edit Weighing Session")
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Session updated successfully."))
        return super().form_valid(form)


class WeighingSessionDeleteView(
    LoginRequiredMixin, HandleProtectedErrorMixin, DeleteView
):
    model = WeighingSession
    template_name = "weight/session_confirm_delete.html"
    success_url = reverse_lazy(SESSION_LIST_URL)

    def delete(self, request, *args, **kwargs):
        # Default implementation or simple pass, logic moved to post
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.soft_delete()
            messages.success(request, _("Session moved to trash."))
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return redirect(self.success_url)


class WeighingSessionTrashListView(LoginRequiredMixin, ListView):
    model = WeighingSession
    template_name = "weight/session_trash.html"
    context_object_name = "sessions"

    def get_queryset(self):
        return WeighingSession.all_objects.filter(is_deleted=True).order_by("-date")


class WeighingSessionRestoreView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            session = WeighingSession.all_objects.get(pk=pk, is_deleted=True)
            session.restore()
            messages.success(request, _("Session restored successfully."))
        except WeighingSession.DoesNotExist:
            messages.error(request, SESSION_NOT_FOUND_MSG)

        return redirect(reverse_lazy(SESSION_LIST_URL))


class WeighingSessionHardDeleteView(
    LoginRequiredMixin, HandleProtectedErrorMixin, View
):
    def post(self, request, pk):
        try:
            session = WeighingSession.all_objects.get(pk=pk, is_deleted=True)
            session.delete(destroy=True)
            messages.success(request, _("Session permanently deleted."))
        except (ValidationError, ProtectedError) as e:
            # Need to fetch object to render template
            session = WeighingSession.all_objects.get(pk=pk, is_deleted=True)
            self.object = session
            return self.handle_delete_error(
                request,
                e,
                template_name="weight/session_confirm_permanent_delete.html",
                context_object_name="session",
            )
        except WeighingSession.DoesNotExist:
            messages.error(request, SESSION_NOT_FOUND_MSG)

        return redirect(reverse_lazy("weight:session-trash"))

    def get(self, request, pk):
        try:
            session = WeighingSession.all_objects.get(pk=pk, is_deleted=True)
            return render(
                request,
                "weight/session_confirm_permanent_delete.html",
                {"session": session},
            )
        except WeighingSession.DoesNotExist:
            messages.error(request, SESSION_NOT_FOUND_MSG)
            return redirect(reverse_lazy("weight:session-trash"))
