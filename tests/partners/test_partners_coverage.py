from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.partners.models import Partner
from apps.sales.models import Sale


@pytest.mark.django_db
class TestPartnersCoverage:

    def test_partner_model_sales_validation(self):
        """Test Partner.delete() validation for sales (line 35)."""
        partner = baker.make(Partner, is_customer=True)
        # Create a sale linked to this partner
        baker.make(Sale, partner=partner)

        # Should raise ValidationError due to associated sales
        with pytest.raises(ValidationError) as exc_info:
            partner.delete()
        assert "associated Sales" in str(exc_info.value)

    def test_partner_delete_view_protected_error(self, client, django_user_model):
        """Test PartnerDeleteView ProtectedError handling (lines 140, 149)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner)

        url = reverse("partners:delete", kwargs={"pk": partner.pk})

        # Mock service to raise ProtectedError
        with patch(
            "apps.partners.services.partner_service.PartnerService.delete_partner",
            side_effect=ProtectedError("Protected", None),
        ):
            response = client.post(url)
            assert response.status_code == 200
            assert "error" in response.context
            assert (
                "Cannot delete this partner because it is referenced"
                in response.context["error"]
            )

    def test_partner_delete_view_validation_error(self, client, django_user_model):
        """Test PartnerDeleteView ValidationError handling (lines 140, 149)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner)

        url = reverse("partners:delete", kwargs={"pk": partner.pk})

        # Mock service to raise ValidationError with messages attribute
        error = ValidationError(["Custom validation message"])
        with patch(
            "apps.partners.services.partner_service.PartnerService.delete_partner",
            side_effect=error,
        ):
            response = client.post(url)
            assert response.status_code == 200
            assert "error" in response.context
            assert "Custom validation message" in response.context["error"]

    def test_partner_hard_delete_view_protected_error(self, client, django_user_model):
        """Test PartnerPermanentDeleteView ProtectedError handling (lines 93-100)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner)
        partner.delete()  # Soft delete first

        url = reverse("partners:hard-delete", kwargs={"pk": partner.pk})

        # Mock service to raise ProtectedError
        with patch(
            "apps.partners.services.partner_service.PartnerService.hard_delete_partner",
            side_effect=ProtectedError("Protected", None),
        ):
            response = client.post(url)
            assert response.status_code == 200
            assert "error" in response.context
            assert (
                "Cannot delete this partner because it is referenced"
                in response.context["error"]
            )

    def test_partner_hard_delete_view_validation_error(self, client, django_user_model):
        """Test PartnerPermanentDeleteView ValidationError handling (lines 93-100)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner)
        partner.delete()  # Soft delete first

        url = reverse("partners:hard-delete", kwargs={"pk": partner.pk})

        # Mock service to raise ValidationError with messages attribute
        error = ValidationError(["Custom validation message"])
        with patch(
            "apps.partners.services.partner_service.PartnerService.hard_delete_partner",
            side_effect=error,
        ):
            response = client.post(url)
            assert response.status_code == 200
            assert "error" in response.context
            assert "Custom validation message" in response.context["error"]

    def test_partner_delete_view_delete_method(self, client, django_user_model):
        """Test PartnerDeleteView delete() method (line 140)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner)

        url = reverse("partners:delete", kwargs={"pk": partner.pk})

        # Use DELETE method instead of POST to hit line 140
        response = client.delete(url)

        # Should successfully delete and redirect
        assert response.status_code == 302
        assert response.url == reverse("partners:list")
