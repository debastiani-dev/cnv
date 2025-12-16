from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.db.models import ProtectedError
from django.test import RequestFactory
from django.urls import reverse
from model_bakery import baker

from apps.authentication.models import User
from apps.cattle.models import Cattle
from apps.health.models import HealthProtocol, Medication, MedicationType, SanitaryEvent
from apps.health.views.protocol_views import ProtocolDeleteView


@pytest.mark.django_db
class TestProtocolListView:
    def test_protocol_list_view(self, client):
        """Test protocol list view (line 34)."""
        user = baker.make(User)
        client.force_login(user)

        # Create some protocols
        baker.make(HealthProtocol, name="Protocol 1", is_deleted=False)
        baker.make(HealthProtocol, name="Protocol 2", is_deleted=False)
        baker.make(HealthProtocol, name="Deleted Protocol", is_deleted=True)

        url = reverse("health:protocol-list")
        response = client.get(url)

        assert response.status_code == 200
        assert len(response.context["protocols"]) == 2  # Only non-deleted


@pytest.mark.django_db
class TestProtocolCreateView:
    def test_protocol_create_get(self, client):
        """Test create view GET request (lines 44-49)."""
        user = baker.make(User)
        client.force_login(user)

        url = reverse("health:protocol-create")
        response = client.get(url)

        assert response.status_code == 200
        assert "items" in response.context  # Formset

    def test_protocol_create_post_valid(self, client):
        """Test create view POST with valid data including formset (lines 46, 52-60)."""
        user = baker.make(User)
        client.force_login(user)
        medication = baker.make(Medication, name="Test Med")

        url = reverse("health:protocol-create")
        data = {
            "name": "New Protocol",
            "description": "Test protocol",
            "is_active": True,
            # Formset management form
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            # First item
            "items-0-medication": medication.pk,
            "items-0-default_dosage": "5ml",
            "items-0-notes": "Test notes",
        }

        client.post(url, data, follow=True)

        # Should create protocol and redirect
        assert HealthProtocol.objects.filter(name="New Protocol").exists()
        protocol = HealthProtocol.objects.get(name="New Protocol")
        assert protocol.items.count() == 1


@pytest.mark.django_db
class TestProtocolUpdateView:
    def test_protocol_update_get(self, client):
        """Test update view GET request (lines 70-75)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, name="Test Protocol")

        url = reverse("health:protocol-update", kwargs={"pk": protocol.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "items" in response.context  # Formset with instance

    def test_protocol_update_post(self, client):
        """Test update view POST request (lines 78-85)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, name="Old Name")

        url = reverse("health:protocol-update", kwargs={"pk": protocol.pk})
        data = {
            "name": "New Name",
            "description": "Updated",
            "is_active": True,
            # Formset management form
            "items-TOTAL_FORMS": "0",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
        }

        client.post(url, data, follow=True)

        protocol.refresh_from_db()
        assert protocol.name == "New Name"


@pytest.mark.django_db
class TestProtocolDetailView:
    def test_protocol_detail_view(self, client):
        """Test detail view (line 94)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, name="Test Protocol", is_deleted=False)

        url = reverse("health:protocol-detail", kwargs={"pk": protocol.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["protocol"] == protocol


@pytest.mark.django_db
class TestProtocolDeleteView:
    def test_protocol_delete_get(self, client):
        """Test delete view GET (lines 104)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol)

        url = reverse("health:protocol-delete", kwargs={"pk": protocol.pk})
        response = client.get(url)

        assert response.status_code == 200

    def test_protocol_soft_delete(self, client):
        """Test soft delete (lines 107-110)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol)

        url = reverse("health:protocol-delete", kwargs={"pk": protocol.pk})
        client.post(url, follow=True)

        protocol.refresh_from_db()
        assert protocol.is_deleted is True

    def test_protocol_delete_method_direct(self):
        """Test calling the delete() method directly (lines 107-110)."""
        user = baker.make(User)
        protocol = baker.make(HealthProtocol)

        # Create a proper request with session and messages
        factory = RequestFactory()
        request = factory.post(
            reverse("health:protocol-delete", kwargs={"pk": protocol.pk})
        )
        request.user = user

        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()

        # Add messages
        setattr(request, "_messages", FallbackStorage(request))

        # Create view instance and call delete directly
        view = ProtocolDeleteView()
        view.request = request
        view.kwargs = {"pk": protocol.pk}
        view.success_url = reverse("health:protocol-list")
        response = view.delete(request, pk=protocol.pk)

        # Check protocol was soft deleted
        protocol.refresh_from_db()
        assert protocol.is_deleted is True
        assert response.status_code == 302  # Redirect

    def test_protocol_delete_protected_error(self):
        """Test ProtectedError during soft delete (lines 111-117)."""
        user = baker.make(User)
        protocol = baker.make(HealthProtocol)

        # Create a proper request with session and messages
        factory = RequestFactory()
        request = factory.post(
            reverse("health:protocol-delete", kwargs={"pk": protocol.pk})
        )
        request.user = user

        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()

        # Add messages
        setattr(request, "_messages", FallbackStorage(request))

        # Mock soft_delete to raise ProtectedError
        with patch.object(
            HealthProtocol, "soft_delete", side_effect=ProtectedError("Protected", [])
        ):
            # Create view instance and call delete directly
            view = ProtocolDeleteView()
            view.request = request
            view.kwargs = {"pk": protocol.pk}
            view.success_url = reverse("health:protocol-list")
            response = view.delete(request, pk=protocol.pk)

            # Check redirect happened
            assert response.status_code == 302
            # Check error message was added
            messages_list = list(get_messages(request))
            assert len(messages_list) > 0
            assert (
                "cannot delete" in str(messages_list[0]).lower()
                or "being used" in str(messages_list[0]).lower()
            )

    def test_protocol_delete_generic_exception(self):
        """Test generic exception during soft delete (lines 118-122)."""
        user = baker.make(User)
        protocol = baker.make(HealthProtocol)

        # Create a proper request with session and messages
        factory = RequestFactory()
        request = factory.post(
            reverse("health:protocol-delete", kwargs={"pk": protocol.pk})
        )
        request.user = user

        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()

        # Add messages
        setattr(request, "_messages", FallbackStorage(request))

        # Mock soft_delete to raise generic exception
        with patch.object(
            HealthProtocol, "soft_delete", side_effect=ValueError("Test error")
        ):
            # Create view instance and call delete directly
            view = ProtocolDeleteView()
            view.request = request
            view.kwargs = {"pk": protocol.pk}
            view.success_url = reverse("health:protocol-list")
            response = view.delete(request, pk=protocol.pk)

            # Check redirect happened
            assert response.status_code == 302
            # Check error message was added
            messages_list = list(get_messages(request))
            assert len(messages_list) > 0
            assert "error" in str(messages_list[0]).lower()


@pytest.mark.django_db
class TestProtocolTrashViews:
    def test_trash_list_view(self, client):
        """Test trash list view (line 134)."""
        user = baker.make(User)
        client.force_login(user)

        baker.make(HealthProtocol, is_deleted=True)
        baker.make(HealthProtocol, is_deleted=False)

        url = reverse("health:protocol-trash")
        response = client.get(url)

        assert response.status_code == 200
        assert len(response.context["protocols"]) == 1

    def test_protocol_restore(self, client):
        """Test protocol restore (lines 139-142)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, is_deleted=True)

        url = reverse("health:protocol-restore", kwargs={"pk": protocol.pk})
        client.get(url, follow=True)

        protocol.refresh_from_db()
        assert protocol.is_deleted is False

    def test_hard_delete_get(self, client):
        """Test hard delete GET redirect (lines 147-148)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, is_deleted=True)

        url = reverse("health:protocol-hard-delete", kwargs={"pk": protocol.pk})
        response = client.get(url)

        assert response.status_code == 302  # Redirect

    def test_hard_delete_post(self, client):
        """Test hard delete POST (lines 153-156)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, is_deleted=True)

        url = reverse("health:protocol-hard-delete", kwargs={"pk": protocol.pk})
        client.post(url, follow=True)

        assert HealthProtocol.all_objects.filter(pk=protocol.pk).exists() is False

    def test_hard_delete_protected_error(self, client):
        """Test ProtectedError during hard delete (line 158)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, is_deleted=True)

        # Create something that references the protocol to cause ProtectedError
        # The protocol has items, so deleting with destroy=False should work,
        # but we'll mock to force ProtectedError

        with patch.object(
            type(protocol), "delete", side_effect=ProtectedError("Cannot delete", [])
        ):
            url = reverse("health:protocol-hard-delete", kwargs={"pk": protocol.pk})
            response = client.post(url, follow=True)

            assert response.status_code == 200
            # Error message should be displayed
            messages_list = list(response.context["messages"])
            assert len(messages_list) > 0
            assert (
                "cannot" in str(messages_list[0]).lower()
                or "referenced" in str(messages_list[0]).lower()
            )

    def test_hard_delete_generic_exception(self, client):
        """Test generic exception during hard delete (lines 164-168)."""
        user = baker.make(User)
        client.force_login(user)
        protocol = baker.make(HealthProtocol, is_deleted=True)
        protocol_pk = protocol.pk

        # Create a mock that only raises on delete
        def mock_delete(self, destroy=False):
            raise ValueError("Test error")

        with patch.object(HealthProtocol, "delete", mock_delete):
            url = reverse("health:protocol-hard-delete", kwargs={"pk": protocol_pk})
            response = client.post(url, follow=True)

            assert response.status_code == 200
            # Error message should be displayed
            messages_list = list(response.context["messages"])
            assert len(messages_list) > 0
            assert "error" in str(messages_list[0]).lower()


@pytest.mark.django_db
class TestProtocolApplyView:
    def setup_method(self):
        self.url = reverse("health:protocol-apply")
        self.user = baker.make(User, username="testuser")
        self.protocol = baker.make(HealthProtocol, name="Test Protocol", is_active=True)
        # Add item to protocol
        self.medication = baker.make(
            Medication, name="Med1", medication_type=MedicationType.VACCINE
        )
        baker.make(
            "health.ProtocolItem",
            protocol=self.protocol,
            medication=self.medication,
            default_dosage="10ml",
        )
        self.cattle_list = baker.make(Cattle, _quantity=3)
        self.cattle_ids = [c.pk for c in self.cattle_list]

    def test_apply_view_setup_phase(self, client):
        """Test the initial POST from cattle list (Setup Phase)"""
        client.force_login(self.user)
        data = {"cattle_ids": self.cattle_ids}
        response = client.post(self.url, data)

        assert response.status_code == 200
        assert "health/protocol_apply.html" in [t.name for t in response.templates]
        assert response.context["cattle_count"] == 3
        # Check that cattle IDs are in the response
        content_str = str(response.content)
        assert str(self.cattle_ids[0]) in content_str

    def test_apply_view_perform_phase(self, client):
        """Test the final POST to apply protocol (Perform Phase)"""
        client.force_login(self.user)

        cattle_ids_str = ",".join(map(str, self.cattle_ids))
        data = {
            "perform_application": "1",
            "cattle_ids_str": cattle_ids_str,
            "protocol": self.protocol.pk,
            "date": "2023-10-27",
            "performed_by": self.user.pk,
        }

        response = client.post(self.url, data, follow=True)

        assert response.status_code == 200  # Redirect followed

        # Check assertions
        assert SanitaryEvent.objects.count() == 1  # 1 Header Event
        event = SanitaryEvent.objects.first()
        assert event.targets.count() == 3  # 3 Cattle Targets

    def test_apply_view_no_cattle_selected(self, client):
        client.force_login(self.user)
        data = {}  # No cattle_ids
        response = client.post(self.url, data, follow=True)
        # Should redirect back to list with warning
        assert response.status_code == 200

    def test_apply_view_perform_no_cattle(self, client):
        """Test perform phase with no cattle IDs (lines 188-190)."""
        client.force_login(self.user)

        data = {
            "perform_application": "1",
            "cattle_ids_str": "",  # Empty
            "protocol": self.protocol.pk,
            "date": "2023-10-27",
            "performed_by": self.user.pk,
        }

        response = client.post(self.url, data, follow=True)

        assert response.status_code == 200
        # Should show error message

    def test_apply_view_perform_exception(self, client):
        """Test exception during protocol application (lines 206-211)."""
        client.force_login(self.user)

        cattle_ids_str = ",".join(map(str, self.cattle_ids))
        data = {
            "perform_application": "1",
            "cattle_ids_str": cattle_ids_str,
            "protocol": self.protocol.pk,
            "date": "2023-10-27",
            "performed_by": self.user.pk,
        }

        # Mock apply_protocol to raise exception
        with patch(
            "apps.health.views.protocol_views.ProtocolService.apply_protocol",
            side_effect=ValueError("Test error"),
        ):
            response = client.post(self.url, data, follow=True)

            assert response.status_code == 200
            # Error message should be displayed
            messages_list = list(response.context["messages"])
            assert len(messages_list) > 0
            assert "error" in str(messages_list[0]).lower()

    def test_apply_view_perform_invalid_form(self, client):
        """Test perform phase with invalid form (lines 213-225)."""
        client.force_login(self.user)

        cattle_ids_str = ",".join(map(str, self.cattle_ids))
        data = {
            "perform_application": "1",
            "cattle_ids_str": cattle_ids_str,
            # Missing required fields
            "date": "invalid-date",
        }

        response = client.post(self.url, data)

        assert response.status_code == 200
        assert "form" in response.context
