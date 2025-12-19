from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from apps.cattle.models import Cattle


class HandleProtectedErrorMixin:
    """
    Mixin to handle ProtectedError/ValidationError during deletion.
    """

    def handle_delete_error(
        self, request, exception, template_name=None, context_object_name="object"
    ):
        error_message = (
            exception.message if hasattr(exception, "message") else str(exception)
        )
        if hasattr(exception, "messages"):
            error_message = str(exception.messages[0])
        elif isinstance(exception, ProtectedError):
            error_message = _(
                "Cannot delete this object because it is referenced by other objects."
            )

        context = {
            "error": error_message,
        }
        # Try to use self.object if available/relevant, or fetch if needed (views usually have self.object set)
        obj = getattr(self, "object", None)
        if obj:
            context[context_object_name] = obj

        target_template = template_name or self.template_name
        return render(request, target_template, context)


class SafeDeleteMixin(HandleProtectedErrorMixin):
    """
    Mixin to safely delete objects, handling ProtectedError/ValidationError
    and redirecting on success.
    Requires:
        - get_object() method (from SingleObjectMixin/DeleteView)
        - get_success_url() method (from DeletionMixin/DeleteView)
    """

    def delete(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
        except (ValidationError, ProtectedError) as e:
            return self.handle_delete_error(request, e)
        return HttpResponseRedirect(self.get_success_url())


class CattleBulkActionMixin:
    """
    Mixin to handle bulk actions for cattle selection.
    Handles:
    - Retrieving cattle IDs from GET/POST.
    - Setting initial form data.
    - Populating context with selected cattle.
    - Handling empty selection (redirect to list).
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

    def validate_cattle_selection(self, form):
        """
        Validates that cattle_ids are present and valid.
        Returns the list of matching cattle objects if valid.
        Raises ValidationError if invalid.
        """
        cattle_ids_str = form.cleaned_data.get("cattle_ids")
        if not cattle_ids_str:
            raise ValidationError(_("No cattle selected."))

        cattle_ids = cattle_ids_str.split(",")
        cattle_list = list(Cattle.objects.filter(pk__in=cattle_ids))

        if not cattle_list:
            raise ValidationError(_("Invalid cattle selection."))

        return cattle_list

    def get_valid_cattle_list(self, form):
        """
        Validates the cattle in the form and returns the list.
        Handles messaging and ValidationErrors internally.
        Returns None if invalid.
        """
        try:
            return self.validate_cattle_selection(form)
        except ValidationError as e:
            messages.error(self.request, str(e.message))
            return None

    def handle_initial_batch_post(self, request):
        """
        Handles the initial POST request from the cattle list bulk action.
        Validates selection and renders the form with initial data.
        """
        cattle_ids = self._get_cattle_ids()
        if not cattle_ids:
            messages.error(request, _("No cattle selected."))
            return redirect("cattle:list")

        # Initialize form with the cattle IDs
        form = self.form_class(initial={"cattle_ids": ",".join(cattle_ids)})
        self.object = None
        return self.render_to_response(self.get_context_data(form=form))

    def _get_cattle_ids(self):
        ids_list = self.request.GET.getlist("cattle_ids")
        if ids_list:
            return ids_list

        ids_list = self.request.POST.getlist("cattle_ids")

        if len(ids_list) > 1:
            return ids_list

        if len(ids_list) == 1:
            val = ids_list[0]
            if "," in val:
                return val.split(",")
            return [val]

        return []
