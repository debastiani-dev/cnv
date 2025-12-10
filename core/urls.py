"""
URL configuration for cnv project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("apps.authentication.urls", namespace="authentication")),
    path("cattle/", include("apps.cattle.urls", namespace="cattle")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("partners/", include("apps.partners.urls", namespace="partners")),
    path("sales/", include("apps.sales.urls", namespace="sales")),
    path("purchases/", include("apps.purchases.urls", namespace="purchases")),
    path("health/", include("apps.health.urls", namespace="health")),
    path("reproduction/", include("apps.reproduction.urls", namespace="reproduction")),
    path("weight/", include("apps.weight.urls", namespace="weight")),
    path("rosetta/", include("rosetta.urls")),
    path("", include("apps.website.urls", namespace="website")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # type: ignore

    if "rosetta" in settings.INSTALLED_APPS:
        try:
            pass
            # path("rosetta/", include("rosetta.urls")) is already in main list
        except ImportError:
            pass
