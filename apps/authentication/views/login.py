from django.contrib.auth import views as auth_views
from django.utils.translation import gettext as _


class LoginView(auth_views.LoginView):
    template_name = "authentication/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = _("Login")
        return context



class LogoutView(auth_views.LogoutView):
    pass
