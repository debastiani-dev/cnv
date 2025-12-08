from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views import View


class ItemLookupView(LoginRequiredMixin, View):
    def get(self, request):
        content_type_id = request.GET.get("content_type_id")
        if not content_type_id:
            return JsonResponse({"error": "Missing content_type_id"}, status=400)

        try:
            ct = ContentType.objects.get_for_id(content_type_id)
        except ContentType.DoesNotExist:
            return JsonResponse({"error": "Invalid content_type_id"}, status=404)

        # Security/Whitelist check (Optional but good practice)
        # For now, allow 'cattle', 'machinery' (future)
        allowed_models = ["cattle"]
        if ct.model not in allowed_models:
            return JsonResponse(
                {"error": "Model not allowed for sale lookup"}, status=403
            )

        model_class = ct.model_class()

        # Filter for available items (not deleted, potentially not sold)
        # Assuming most sellable items have 'is_deleted' from BaseModel
        qs = model_class.objects.all()
        if hasattr(model_class, "is_deleted"):
            qs = qs.filter(is_deleted=False)

        # Return list
        data = [{"id": str(obj.pk), "name": str(obj)} for obj in qs]
        return JsonResponse({"results": data})
