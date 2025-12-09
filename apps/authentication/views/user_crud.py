from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    RedirectView,
    UpdateView,
)

from ..forms import UserForm, UserUpdateSelfForm
from ..permissions import AdminOrSelfMixin, AdminRequiredMixin
from ..services.user_service import UserService

User = get_user_model()


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = User
    template_name = "authentication/user_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        return UserService.get_all_users()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Users")
        context["segment"] = "users"
        return context


class UserDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    model = User
    template_name = "authentication/user_detail.html"
    context_object_name = "target_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("User Details")
        context["segment"] = "users"
        return context


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = User
    form_class = UserForm
    template_name = "authentication/user_form.html"
    success_url = reverse_lazy("authentication:user-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Create User")
        context["segment"] = "users"
        return context


class UserUpdateView(LoginRequiredMixin, AdminOrSelfMixin, UpdateView):
    model = User
    template_name = "authentication/user_form.html"

    def get_form_class(self):
        # If user is admin, they can edit everything using UserForm
        if self.request.user.is_superuser:
            return UserForm
        # Regular users can only edit limited fields
        return UserUpdateSelfForm

    def get_success_url(self):
        if self.request.user.is_superuser:
            return reverse_lazy("authentication:user-list")
        # Self-update redirects back to the form (or dashboard)
        return reverse_lazy("dashboard:home")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Update User")
        if self.request.user.is_superuser:
            context["segment"] = "users"
        return context


class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = User
    template_name = "authentication/user_confirm_delete.html"
    success_url = reverse_lazy("authentication:user-list")
    permission_required = "authentication.delete_user"
    context_object_name = "target_user"

    def form_valid(self, form):
        messages.success(self.request, _("User deleted successfully."))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Delete User")
        context["segment"] = "users"
        context["segment"] = "users"
        return context

    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            # We call delete on the object directly to trigger model validation
            self.object.delete()
            messages.success(self.request, _("User deleted successfully."))
        except ValidationError as e:
            return render(
                request,
                self.template_name,
                {
                    "target_user": self.object,
                    "error": e.message if hasattr(e, "message") else str(e.messages[0]),
                },
            )
        return HttpResponseRedirect(self.success_url)


class UserTrashView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = "authentication/user_trash_list.html"
    context_object_name = "users"
    permission_required = "authentication.view_user"

    def get_queryset(self):
        # We need a custom manager logic or filter here because default objects might filter out deleted?
        # apps/base/models/base_model.py: BaseManager filters is_deleted=False.
        # User inherits BaseModel.
        # So User.objects.all() returns only active.
        # We need User.all_objects.filter(is_deleted=True).
        # Assuming BaseModel has all_objects manager.
        return User.all_objects.filter(is_deleted=True).order_by("-created_at")


class UserRestoreView(LoginRequiredMixin, PermissionRequiredMixin, RedirectView):
    permission_required = "authentication.delete_user"  # restore is basically un-delete
    url = reverse_lazy("authentication:user-trash")  # type: ignore

    def get_redirect_url(self, *args, **kwargs):
        return reverse_lazy("authentication:user-trash")

    def post(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        user = get_object_or_404(User.all_objects, pk=pk, is_deleted=True)
        user.restore()
        messages.success(request, _("User restored successfully."))
        return super().post(request, *args, **kwargs)


class UserDeletePermanentView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = User
    template_name = "authentication/user_confirm_permanent_delete.html"
    success_url = reverse_lazy("authentication:user-trash")
    permission_required = "authentication.delete_user"

    def get_queryset(self):
        return User.all_objects.filter(is_deleted=True)

    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete(destroy=True)
            messages.success(self.request, _("User permanently deleted."))
        except ValidationError as e:
            return render(
                request,
                self.template_name,
                {
                    "target_user": self.object,
                    "error": e.message if hasattr(e, "message") else str(e.messages[0]),
                },
            )
        return HttpResponseRedirect(self.success_url)
