import pytest
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from apps.authentication.models import User
from apps.base.views.api import ItemLookupView
from apps.cattle.models import Cattle


@pytest.mark.django_db
class TestItemLookupView:
    def setup_method(self):
        self.factory = RequestFactory()
        # Use a unique username to avoid conflicts if DB is not flushed perfectly or parallel tests
        self.user = User.objects.create_superuser(
            "admin_test_api", "admin_api@example.com", "pass"
        )
        self.view = ItemLookupView.as_view()

    def test_missing_content_type(self):
        request = self.factory.get("/api/lookup/")
        request.user = self.user
        response = self.view(request)
        assert response.status_code == 400
        assert b"Missing content_type_id" in response.content

    def test_invalid_content_type(self):
        request = self.factory.get("/api/lookup/", {"content_type_id": 99999})
        request.user = self.user
        response = self.view(request)
        assert response.status_code == 404
        assert b"Invalid content_type_id" in response.content

    def test_not_allowed_model(self):
        # User model is not in the whitelist
        ct = ContentType.objects.get_for_model(User)
        request = self.factory.get("/api/lookup/", {"content_type_id": ct.id})
        request.user = self.user
        response = self.view(request)
        assert response.status_code == 403
        assert b"Model not allowed" in response.content

    def test_allowed_model_success(self):
        ct = ContentType.objects.get_for_model(Cattle)
        # Create a sample cow
        Cattle.objects.create(tag="TEST-COW", name="Test Cow")

        request = self.factory.get("/api/lookup/", {"content_type_id": ct.id})
        request.user = self.user
        response = self.view(request)

        assert response.status_code == 200
        assert b"TEST-COW" in response.content

    def test_is_deleted_filtering(self):
        """Test that objects with is_deleted=True are filtered out."""
        # Create two cows, one deleted
        ct = ContentType.objects.get_for_model(Cattle)
        Cattle.objects.create(tag="VISIBLE", name="Visible Cow")
        Cattle.objects.create(tag="DELETED", name="Deleted Cow", is_deleted=True)

        request = self.factory.get("/api/lookup/", {"content_type_id": ct.id})
        request.user = self.user
        response = self.view(request)

        assert response.status_code == 200
        content = response.content.decode()
        assert "VISIBLE" in content
        assert "DELETED" not in content
