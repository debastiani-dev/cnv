import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.authentication.models.user import User


@pytest.mark.django_db
class TestUserDeletionValidation:

    def test_cannot_delete_last_superuser(self):
        # Create a single superuser
        user = baker.make(User, is_superuser=True)

        # Verify no other superusers exist
        assert User.objects.filter(is_superuser=True).count() == 1

        # Attempt to delete
        with pytest.raises(ValidationError) as excinfo:
            user.delete()

        assert "Cannot delete the last active superuser" in str(excinfo.value)

    def test_can_delete_superuser_if_others_exist(self):
        # Create two superusers
        user1 = baker.make(User, is_superuser=True)
        baker.make(User, is_superuser=True)

        # Delete one
        user1.delete()

        # Verify it's deleted (soft delete by default)
        user1.refresh_from_db()
        assert user1.is_deleted is True

        # user2 should still be active
        assert User.objects.filter(is_superuser=True, is_deleted=False).count() == 1

    def test_user_delete_view_handles_validation_error(self, client):
        # Create a single superuser and login
        user = baker.make(User, is_superuser=True)
        client.force_login(user)

        url = reverse("authentication:user-delete", kwargs={"pk": user.pk})

        # Ensure only 1 superuser
        assert User.objects.filter(is_superuser=True).count() == 1

        response = client.post(url)

        # Should re-render template with error, not redirect
        assert response.status_code == 200
        assert "authentication/user_confirm_delete.html" in [
            t.name for t in response.templates
        ]
        assert "Cannot delete the last active superuser" in response.context["error"]

        # User should still be active
        user.refresh_from_db()
        assert not user.is_deleted

    def test_user_permanent_delete_view_handles_validation_error(self, client):
        # pylint: disable=import-outside-toplevel
        from django.contrib.auth.models import Permission

        # Create a deleted superuser (target)
        target_user = baker.make(User, is_superuser=True, is_deleted=True)

        # Create a staff user to perform the action
        staff_user = baker.make(User, is_staff=True, is_superuser=False)
        perm = Permission.objects.get(codename="delete_user")
        staff_user.user_permissions.add(perm)

        client.force_login(staff_user)
        url = reverse(
            "authentication:user-permanent-delete", kwargs={"pk": target_user.pk}
        )

        response = client.post(url)

        # Should block hard delete too
        assert response.status_code == 200
        assert "authentication/user_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]
        assert "Cannot delete the last active superuser" in response.context["error"]

        # User should still exist
        assert User.all_objects.filter(pk=target_user.pk).exists()
