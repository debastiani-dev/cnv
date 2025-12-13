from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.sales.models import Sale
from tests.test_utils import get_invalid_transaction_data, get_valid_sales_form_data


@pytest.mark.django_db
class TestSalesCoverage:

    def test_create_view_exception_handling(self, client, django_user_model):
        """Test exception handling in SaleCreateView."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make("partners.Partner", is_customer=True)

        url = reverse("sales:create")

        # Valid data to pass form validation
        data = get_valid_sales_form_data(partner, "Test Note")
        data.update(
            {
                "date": "2024-01-01",
                # We need at least one valid item to trigger save logic
                "items-0-content_type": ContentType.objects.get_for_model(Cattle).pk,
                "items-0-object_id": baker.make("cattle.Cattle").uuid,
                "items-0-quantity": 1,
                "items-0-unit_price": "100.00",
            }
        )

        # Mock create_sale_from_forms to raise Exception
        with patch(
            "apps.sales.services.sale_service.SaleService.create_sale_from_forms",
            side_effect=Exception("Simulated Error"),
        ):
            # Mock validation to succeed
            with patch(
                "apps.sales.services.sale_service.SaleService.validate_item_for_sale"
            ):
                response = client.post(url, data)
                assert response.status_code == 200
                assert response.context["form"].non_field_errors()
                assert (
                    "Simulated Error" in response.context["form"].non_field_errors()[0]
                )

    def test_update_view_get_context_no_post(self, client, django_user_model):
        """Test UpdateView GET context (line 99)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        sale = baker.make(Sale)

        url = reverse("sales:update", kwargs={"pk": sale.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "items" in response.context
        assert response.context["items"].instance == sale

    def test_update_view_form_invalid(self, client, django_user_model):
        """Test UpdateView form_invalid (line 123) and item form validation error (forms.py 86-91)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        sale = baker.make(Sale)

        url = reverse("sales:update", kwargs={"pk": sale.pk})

        # Invalid data (missing required fields) triggers form_invalid
        data = get_invalid_transaction_data()
        response = client.post(url, data)
        assert response.status_code == 200
        assert response.context["form"].errors

    def test_update_view_valid_form_invalid_items(self, client, django_user_model):
        """Test UpdateView when main form is valid but items are invalid (hits line 123)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make("partners.Partner", is_customer=True)
        sale = baker.make(Sale, partner=partner)

        url = reverse("sales:update", kwargs={"pk": sale.pk})

        # Valid main form data
        data = {
            "date": "2024-01-01",
            "partner": partner.pk,
            "notes": "Valid Note",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            # Invalid Item (missing required content_type/object_id if quantity provided, or just invalid quantity)
            "items-0-quantity": -1,  # Invalid quantity
            "items-0-unit_price": "100.00",
            # Missing ContentType/ObjectID might trigger other errors, lets just make formset invalid
        }
        response = client.post(url, data)
        assert response.status_code == 200
        # Main form valid, so no errors there?
        # Actually form_invalid re-renders form with errors.
        # But errors are in items.
        assert not response.context["form"].errors
        assert response.context["items"].errors
        assert any(err for err in response.context["items"].errors)

    def test_item_form_clean_validation_error(self, client, django_user_model):
        """Test SaleItemForm clean method ValidationError handling (forms.py 86-91)."""
        # This is best tested via the CreateView or directly instantiating the form.
        # Let's try via CreateView with mocked validation error.
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make("partners.Partner", is_customer=True)

        # We need a valid item to try validation on
        cow = baker.make("cattle.Cattle")

        url = reverse("sales:create")
        data = {
            "date": "2024-01-01",
            "partner": partner.pk,
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-0-content_type": ContentType.objects.get_for_model(Cattle).pk,
            "items-0-object_id": cow.uuid,  # Form expects UUID
            "items-0-quantity": 1,
            "items-0-unit_price": "100.00",
        }

        # Mock validation to raise ValidationError
        with patch(
            "apps.sales.services.sale_service.SaleService.validate_item_for_sale",
            side_effect=ValidationError("Blocked"),
        ):
            response = client.post(url, data)
            assert response.status_code == 200
            # Check for error in formset
            # Since it's an inline formset, errors are in response.context['items'].errors
            # or implicitly invoked
            assert "items" in response.context
            formset = response.context["items"]
            assert any("Blocked" in str(e) for e in formset.errors)

    def test_create_view_service_exception(self, client, django_user_model):
        """Test CreateView service exception (views.py 79-84)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make("partners.Partner", is_customer=True)
        cow = baker.make("cattle.Cattle")

        url = reverse("sales:create")
        data = {  # Valid Data
            "date": "2024-01-01",
            "partner": partner.pk,
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-0-content_type": ContentType.objects.get_for_model(Cattle).pk,
            "items-0-object_id": cow.uuid,
            "items-0-quantity": 1,
            "items-0-unit_price": "100.00",
        }

        # Mock service.create_sale_from_forms to raise generic Exception
        with patch(
            "apps.sales.services.sale_service.SaleService.create_sale_from_forms",
            side_effect=Exception("Major Fail"),
        ):
            # Also mock validate to pass
            with patch(
                "apps.sales.services.sale_service.SaleService.validate_item_for_sale"
            ):
                response = client.post(url, data)
                assert response.status_code == 200
                assert response.context["form"].non_field_errors()
                assert "Major Fail" in response.context["form"].non_field_errors()[0]
