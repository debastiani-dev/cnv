from django.db.models import ProtectedError
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
