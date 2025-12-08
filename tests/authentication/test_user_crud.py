import pytest
import uuid
from django.urls import reverse
from model_bakery import baker
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def admin_user(db):
    return baker.make(User, is_superuser=True, is_staff=True)

@pytest.fixture
def regular_user(db):
    return baker.make(User, is_superuser=False, is_staff=False)

@pytest.mark.django_db
class TestUserService:
    def test_get_all_users(self, admin_user, regular_user, client):
        client.force_login(admin_user)
        response = client.get(reverse("authentication:user-list"))
        assert response.status_code == 200
        assert len(response.context["users"]) >= 2  # At least admin + regular

    def test_regular_user_cannot_list_users(self, regular_user, client):
        client.force_login(regular_user)
        response = client.get(reverse("authentication:user-list"))
        assert response.status_code == 403

    def test_admin_can_create_user(self, admin_user, client):
        client.force_login(admin_user)
        url = reverse("authentication:user-create")
        data = {
            "username": "newadminuser",
            "password": "strongpassword123",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User"
        }
        response = client.post(url, data)
        assert response.status_code == 302 # Redirects to list
        assert User.objects.filter(username="newadminuser").exists()

    def test_regular_user_cannot_create_user(self, regular_user, client):
        client.force_login(regular_user)
        url = reverse("authentication:user-create")
        response = client.get(url)
        assert response.status_code == 403
        response = client.post(url, {})
        assert response.status_code == 403

    def test_admin_can_update_any_user(self, admin_user, regular_user, client):
        client.force_login(admin_user)
        url = reverse("authentication:user-update", kwargs={"pk": regular_user.pk})
        data = {
            "username": "updated_by_admin",
            "email": regular_user.email,
            "first_name": "AdminEdited",
            "last_name": "User"
        }
        response = client.post(url, data)
        assert response.status_code == 302
        regular_user.refresh_from_db()
        assert regular_user.first_name == "AdminEdited"
        assert regular_user.username == "updated_by_admin"

    def test_regular_user_can_update_self(self, regular_user, client):
        client.force_login(regular_user)
        url = reverse("authentication:user-update", kwargs={"pk": regular_user.pk})
        data = {
            "first_name": "SelfEdited",
            "last_name": "User",
            "email": "self@example.com"
        }
        response = client.post(url, data)
        assert response.status_code == 302
        regular_user.refresh_from_db()
        assert regular_user.first_name == "SelfEdited"
        assert regular_user.email == "self@example.com"

    def test_regular_user_cannot_update_others(self, regular_user, admin_user, client):
        client.force_login(regular_user)
        url = reverse("authentication:user-update", kwargs={"pk": admin_user.pk})
        response = client.get(url)
        assert response.status_code == 403
        
    def test_admin_can_delete_user(self, admin_user, regular_user, client):
        client.force_login(admin_user)
        url = reverse("authentication:user-delete", kwargs={"pk": regular_user.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not User.objects.filter(pk=regular_user.pk).exists()

    def test_regular_user_cannot_delete_user(self, regular_user, admin_user, client):
        client.force_login(regular_user)
        # Try to delete self or admin
        url = reverse("authentication:user-delete", kwargs={"pk": regular_user.pk})
        response = client.post(url)
        assert response.status_code == 403

@pytest.mark.django_db
class TestUserTrashBin:
    def test_trash_list_contains_deleted_users(self, admin_user, regular_user, client):
        # Soft delete regular user
        regular_user.delete() 
        assert regular_user.is_deleted
        
        client.force_login(admin_user)
        url = reverse("authentication:user-trash")
        response = client.get(url)
        
        assert response.status_code == 200
        assert regular_user in response.context["users"]
        assert admin_user not in response.context["users"]

    def test_restore_user(self, admin_user, regular_user, client):
        regular_user.delete()
        assert regular_user.is_deleted
        
        client.force_login(admin_user)
        url = reverse("authentication:user-restore", kwargs={"pk": regular_user.pk})
        response = client.post(url)
        
        assert response.status_code == 302 # Redirects back to trash
        regular_user.refresh_from_db()
        assert not regular_user.is_deleted
        
    def test_permanent_delete_user(self, admin_user, regular_user, client):
        regular_user.delete()
        assert regular_user.is_deleted
        
        client.force_login(admin_user)
        url = reverse("authentication:user-permanent-delete", kwargs={"pk": regular_user.pk})
        response = client.post(url)
        
        assert response.status_code == 302 # Redirects to trash
        
        # Verify completely gone
        assert not User.objects.filter(pk=regular_user.pk).exists()
        assert not User.all_objects.filter(pk=regular_user.pk).exists()
