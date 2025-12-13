import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from model_bakery import baker

from apps.partners.models import Partner
from apps.purchases.models.purchase import Purchase


@pytest.mark.django_db
class TestPartnerViews:
    """Tests for Partner CRUD and trash views."""

    def test_list_view(self, client, user):
        """Test list view with filters."""
        client.force_login(user)
        p1 = baker.make(Partner, name="Alpha", is_supplier=True, is_customer=False)
        p2 = baker.make(Partner, name="Beta", is_supplier=False, is_customer=True)

        # Test basic list
        url = reverse("partners:list")
        response = client.get(url)
        assert response.status_code == 200
        assert p1 in response.context["partners"]
        assert p2 in response.context["partners"]

        # Test search
        response = client.get(url, {"q": "Alpha"})
        assert p1 in response.context["partners"]
        assert p2 not in response.context["partners"]

        # Test role filter
        response = client.get(url, {"role": "supplier"})
        assert p1 in response.context["partners"]
        assert p2 not in response.context["partners"]

        response = client.get(url, {"role": "customer"})
        assert p1 not in response.context["partners"]
        assert p2 in response.context["partners"]

    def test_create_view(self, client, user):
        """Test valid partner creation."""
        client.force_login(user)
        data = {"name": "Gamma Corp", "is_supplier": True, "email": "gamma@example.com"}
        url = reverse("partners:create")
        response = client.post(url, data)

        assert response.status_code == 302
        assert Partner.objects.filter(name="Gamma Corp").exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("created" in str(m).lower() for m in messages)

    def test_update_view(self, client, user):
        """Test valid partner update."""
        client.force_login(user)
        partner = baker.make(Partner, name="Delta Inc")
        data = {
            "name": "Delta Updated",
            "is_supplier": True,
            "email": "delta@example.com",
        }
        url = reverse("partners:update", kwargs={"pk": partner.pk})
        response = client.post(url, data)

        assert response.status_code == 302
        partner.refresh_from_db()
        assert partner.name == "Delta Updated"

        messages = list(get_messages(response.wsgi_request))
        assert any("updated" in str(m).lower() for m in messages)

    def test_delete_view_soft_delete(self, client, user):
        """Test soft delete of partner."""
        client.force_login(user)
        partner = baker.make(Partner)

        url = reverse("partners:delete", kwargs={"pk": partner.pk})
        # Delete view uses post for actual action usually
        response = client.post(url, follow=True)

        assert response.status_code == 200
        assert not Partner.objects.filter(pk=partner.pk).exists()
        assert Partner.all_objects.filter(pk=partner.pk, is_deleted=True).exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("trash" in str(m).lower() for m in messages)

    def test_trash_list_view(self, client, user):
        """Test trash list view."""
        client.force_login(user)
        active = baker.make(Partner, name="Active")
        deleted = baker.make(Partner, name="Deleted")
        deleted.delete()

        url = reverse("partners:trash")
        response = client.get(url)

        assert response.status_code == 200
        assert deleted in response.context["partners"]
        assert active not in response.context["partners"]

    def test_restore_view(self, client, user):
        """Test restore partner."""
        client.force_login(user)
        partner = baker.make(Partner)
        partner.delete()

        url = reverse("partners:restore", kwargs={"pk": partner.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert Partner.objects.filter(pk=partner.pk).exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("restored" in str(m).lower() for m in messages)

    def test_hard_delete_view(self, client, user):
        """Test permanent delete."""
        client.force_login(user)
        partner = baker.make(Partner)
        partner.delete()

        url = reverse("partners:hard-delete", kwargs={"pk": partner.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert not Partner.all_objects.filter(pk=partner.pk).exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("permanently deleted" in str(m).lower() for m in messages)

    def test_delete_protected_error(self, client, user):
        """Test protected error on delete (if applicable)."""
        # If Partner is foreign key to something with on_delete=PROTECT
        # E.g. Purchase.partner uses PROTECT.

        client.force_login(user)
        partner = baker.make(Partner)
        baker.make(Purchase, partner=partner)

        url = reverse("partners:delete", kwargs={"pk": partner.pk})
        response = client.post(url)

        # Should render error instead of redirect
        assert response.status_code == 200
        assert (
            "Cannot delete" in response.content.decode()
            or "referenced" in response.content.decode()
        )
        assert Partner.objects.filter(pk=partner.pk).exists()

    def test_delete_view_get(self, client, user):
        """Test GET request to delete view (confirmation page)."""
        client.force_login(user)
        partner = baker.make(Partner)
        url = reverse("partners:delete", kwargs={"pk": partner.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "partners/partner_confirm_delete.html" in [
            t.name for t in response.templates
        ]

    def test_restore_view_get(self, client, user):
        """Test GET request to restore view (confirmation page)."""
        client.force_login(user)
        partner = baker.make(Partner)
        partner.delete()
        url = reverse("partners:restore", kwargs={"pk": partner.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "partners/partner_confirm_restore.html" in [
            t.name for t in response.templates
        ]

    def test_hard_delete_view_get(self, client, user):
        """Test GET request to hard delete view (confirmation page)."""
        client.force_login(user)
        partner = baker.make(Partner)
        partner.delete()
        url = reverse("partners:hard-delete", kwargs={"pk": partner.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "partners/partner_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]
