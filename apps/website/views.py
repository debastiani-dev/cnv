import os

from django.conf import settings
from django.views.generic import TemplateView


class HomeView(TemplateView):
    template_name = "website/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Define the carousel directory relative to STATIC_ROOT or searching in STATICFILES_DIRS
        # Since this is local dev usually, we check the app's static folder directly for now
        # or use finders if we want to be more robust, but direct path is simpler for the specific app structure.
        # However, listing static files at runtime in production (collectstatic) can be tricky.
        # Assuming we just check the source directory for now as the user is dropping files there.

        # Path: apps/website/static/website/img/carousel
        carousel_dir = os.path.join(
            settings.BASE_DIR, "apps/website/static/website/img/carousel"
        )

        images = []
        if os.path.exists(carousel_dir):
            for filename in sorted(os.listdir(carousel_dir)):
                if filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    images.append(f"website/img/carousel/{filename}")

        context["carousel_images"] = images
        return context
