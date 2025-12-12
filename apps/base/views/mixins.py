from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


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
