import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("password")
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.is_active


@pytest.mark.django_db
class TestAuthenticationViews:
    def test_login_view(self, client):
        user = User.objects.create_user(username="testuser", password="password")
        url = reverse("authentication:login")

        # GET request
        response = client.get(url)
        assert response.status_code == 200
        assert "authentication/login.html" in [t.name for t in response.templates]

        # POST request (Login)
        response = client.post(url, {"username": "testuser", "password": "password"})
        assert response.status_code == 302  # Redirect after login

        # Check if user is authenticated
        # client.login() works, but testing the view post directly does session auth
        assert int(client.session["_auth_user_id"]) == user.id

    def test_logout_view(self, client):
        user = User.objects.create_user(username="testuser", password="password")
        client.force_login(user)
        url = reverse("authentication:logout")

        response = client.post(url)
        # Django 5.0+ logout might require POST or behave differently depending
        # on config, but standard is view is usually post-only or get allowed
        # if configured.
        # auth_views.LogoutView in recent Django allows GET but POST is preferred?
        # Actually in recent Django versions GET is deprecated for logout.
        # Let's try POST.
        assert response.status_code == 302
        assert "_auth_user_id" not in client.session
