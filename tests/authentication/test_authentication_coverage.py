import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.forms import Form
from django.test import RequestFactory
from django.urls import reverse
from model_bakery import baker

from apps.authentication.forms import UserForm
from apps.authentication.services.user_service import UserService
from apps.authentication.views.user_crud import UserDeleteView

User = get_user_model()


@pytest.mark.django_db
class TestUserFormCoverage:
    """Tests to cover missing lines in authentication forms."""

    def test_clean_password_new_user(self):
        """Test UserForm validates password is required for new users (line 40)."""
        # Fixed: Now uses _state.adding instead of checking pk
        # For new users (not saved to DB), password should be required
        form = UserForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                # No password provided
            }
        )

        # Verify instance is new (not saved to DB)
        # pylint: disable=protected-access
        assert form.instance._state.adding, "Instance should be in 'adding' state"

        # Form should be invalid without password
        is_valid = form.is_valid()

        # Line 40 should execute: _state.adding=True and not password => ValidationError
        # pylint: disable=protected-access
        assert not is_valid, f"Form should be invalid. Errors: {form.errors}"
        assert (
            "password" in form.errors
        ), f"Password validation should fail. Errors: {form.errors}"
        assert "required for new users" in str(form.errors["password"])


@pytest.mark.django_db
class TestUserValidationCoverage:
    """Tests to cover missing lines in authentication models."""

    def test_create_superuser_validation_staff_false(self):
        """Test create_superuser raises error if is_staff=False (line 36)."""
        # Try to create superuser with is_staff=False
        with pytest.raises(ValueError) as excinfo:
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="test123",
                is_staff=False,  # This triggers line 36!
            )

        assert "is_staff=True" in str(excinfo.value)

    def test_create_superuser_validation_superuser_false(self):
        """Test create_superuser raises error if is_superuser=False (line 38)."""
        # Try to create superuser with is_superuser=False
        with pytest.raises(ValueError) as excinfo:
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="test123",
                is_superuser=False,  # This triggers line 38!
            )

        assert "is_superuser=True" in str(excinfo.value)

    def test_user_get_short_name(self):
        """Test User.get_short_name method (line 146)."""
        user = baker.make(User, first_name="John", last_name="Doe")

        # Should return first name (line 146)
        assert user.get_short_name() == "John"


@pytest.mark.django_db
class TestUserServiceCoverage:
    """Tests to cover missing lines in authentication services."""

    def test_create_user_no_password(self):
        """Test UserService.create_user raises error without password (lines 28-30)."""

        # Try to create user without password
        with pytest.raises(ValueError) as excinfo:
            UserService.create_user(
                {
                    "username": "testuser",
                    "email": "test@example.com",
                    # No password!
                }
            )

        # Should raise ValueError (lines 28-30)
        assert "Password is required" in str(excinfo.value)

    def test_create_user_with_password(self):
        """Test UserService.create_user with password (line 32)."""

        # Create user with password
        user = UserService.create_user(
            {
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123",
            }
        )

        # Should create successfully (line 32)
        assert user.username == "testuser"
        assert user.check_password("testpass123")

    def test_update_user(self):
        """Test UserService.update_user (lines 39-44)."""

        user = baker.make(User, first_name="Old")

        # Update user
        updated = UserService.update_user(
            user, {"first_name": "New", "last_name": "Name"}
        )

        # Should update fields (lines 39-44)
        assert updated.first_name == "New"
        assert updated.last_name == "Name"

    def test_delete_user(self):
        """Test UserService.delete_user (line 52)."""

        user = baker.make(User)
        user_pk = user.pk

        # Delete user
        UserService.delete_user(user)

        # Should be soft deleted (line 52)
        assert not User.objects.filter(pk=user_pk).exists()
        assert User.all_objects.filter(pk=user_pk, is_deleted=True).exists()


@pytest.mark.django_db
class TestUserViewsCoverage:
    """Tests to cover missing lines in authentication views."""

    def test_user_list_view_filters(self, client):
        """Test UserListView with search query (lines 37, 46, 48)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        client.force_login(admin)

        # Create test users
        baker.make(User, username="john_doe", email="john@example.com")
        baker.make(User, username="jane_smith", email="jane@example.com", is_staff=True)

        # Test with search query (line 37)
        url = reverse("authentication:user-list")
        response = client.get(url, {"q": "john"})
        assert response.status_code == 200

        # Test with role filter staff (line 46)
        response = client.get(url, {"role": "staff"})
        assert response.status_code == 200

        # Test with role filter user (line 48)
        response = client.get(url, {"role": "user"})
        assert response.status_code == 200

    def test_user_detail_view_context(self, client):
        """Test UserDetailView get_context_data (lines 72-75)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        user = baker.make(User)
        client.force_login(admin)

        url = reverse("authentication:user-detail", kwargs={"pk": user.pk})
        response = client.get(url)

        # Should render with context (lines 72-75)
        assert response.status_code == 200
        assert response.context["title"] == "User Details"
        assert response.context["segment"] == "users"

    def test_user_create_view_context(self, client):
        """Test UserCreateView get_context_data (lines 85-88)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        client.force_login(admin)

        url = reverse("authentication:user-create")
        response = client.get(url)

        # Should render with context (lines 85-88)
        assert response.status_code == 200
        assert response.context["title"] == "Create User"
        assert response.context["segment"] == "users"

    def test_user_update_view_context(self, client):
        """Test UserUpdateView get_context_data (lines 109-113)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        user = baker.make(User)
        client.force_login(admin)

        url = reverse("authentication:user-update", kwargs={"pk": user.pk})
        response = client.get(url)

        # Should render with context (lines 109-113)
        assert response.status_code == 200
        assert response.context["title"] == "Update User"
        assert response.context["segment"] == "users"

    def test_user_delete_view_context(self, client):
        """Test UserDeleteView get_context_data (lines 128-131)."""
        # Create 2 superusers so we can delete one
        admin1 = baker.make(User, is_superuser=True, is_staff=True)
        baker.make(User, is_superuser=True, is_staff=True)
        user = baker.make(User)
        client.force_login(admin1)

        url = reverse("authentication:user-delete", kwargs={"pk": user.pk})
        response = client.get(url)

        # Should render with context (lines 128-131)
        assert response.status_code == 200
        assert response.context["title"] == "Delete User"
        assert response.context["segment"] == "users"

    def test_user_delete_view_delete_method(self, client):
        """Test UserDeleteView delete method (line 134)."""
        # Create 2 superusers
        admin = baker.make(User, is_superuser=True, is_staff=True)
        baker.make(User, is_superuser=True, is_staff=True)
        user = baker.make(User)
        client.force_login(admin)

        url = reverse("authentication:user-delete", kwargs={"pk": user.pk})

        # Call DELETE method (line 134 delegates to post)
        response = client.delete(url)
        assert response.status_code == 302

    def test_user_delete_view_form_valid(self):
        """Test UserDeleteView form_valid method (lines 124-125)."""
        # Create users
        admin = baker.make(User, is_superuser=True, is_staff=True)
        baker.make(User, is_superuser=True, is_staff=True)
        user = baker.make(User)

        # Create request with proper middleware
        factory = RequestFactory()
        request = factory.post(f"/auth/users/{user.pk}/delete/")
        request.user = admin

        # Add session middleware
        middleware = SessionMiddleware(lambda x: x)
        middleware.process_request(request)
        request.session.save()

        # Add messages support
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Create view
        view = UserDeleteView()
        view.request = request
        view.kwargs = {"pk": user.pk}
        view.object = user

        # Create a mock form
        mock_form = Form()

        # Directly call form_valid to hit lines 124-125
        response = view.form_valid(mock_form)

        # Lines 124-125 executed:
        # Line 124: messages.success called
        # Line 125: super().form_valid() which does self.object.delete() and redirect
        assert response.status_code == 302
        assert not User.objects.filter(pk=user.pk).exists()

    def test_user_restore_view_post_not_found(self, client):
        """Test UserRestoreView post with non-existent user (line 166)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        client.force_login(admin)

        # Use invalid pk
        url = reverse(
            "authentication:user-restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        # Should allow custom failure handling (e.g. 404)
        assert response.status_code == 404

    def test_user_permanent_delete_post_not_found(self, client):
        """Test UserPermanentDeleteView post with non-existent user (line 188)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        client.force_login(admin)

        # Use invalid pk
        url = reverse(
            "authentication:user-permanent-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        # Should allow custom failure handling (e.g. 404)
        assert response.status_code == 404

    def test_user_permanent_delete_get_not_found(self, client):
        """Test UserPermanentDeleteView get with non-existent user (line 209)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        client.force_login(admin)

        # Use invalid pk
        url = reverse(
            "authentication:user-permanent-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)

        # Should allow custom failure handling (e.g. 404)
        assert response.status_code == 404

    def test_user_permanent_delete_delete_method(self, client):
        """Test that UserPermanentDeleteView supports delete method (line 196)."""
        admin = baker.make(User, is_superuser=True, is_staff=True)
        user = baker.make(User)
        user.delete()  # Soft delete first
        client.force_login(admin)

        url = reverse("authentication:user-permanent-delete", kwargs={"pk": user.pk})

        # Call DELETE method (line 196 delegates to post)
        response = client.delete(url)
        assert response.status_code == 302
        assert not User.all_objects.filter(pk=user.pk).exists()
