import pytest
from django.urls import reverse
from model_bakery import baker

from apps.partners.models import Partner
from apps.purchases.models import Purchase
from tests.test_utils import verify_post_with_mocked_exception


@pytest.mark.django_db
class TestPurchaseCoverage:

    def test_list_view_date_filters(self, client, django_user_model):
        """Test PurchaseListView date filters (lines 41, 43)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Create purchases with different dates
        p1 = baker.make(Purchase, date="2024-01-15")
        p2 = baker.make(Purchase, date="2024-02-15")
        p3 = baker.make(Purchase, date="2024-03-15")

        url = reverse("purchases:list")

        # Test date_after filter (line 41)
        response = client.get(url, {"date_after": "2024-02-01"})
        assert response.status_code == 200
        purchases = list(response.context["purchases"])
        assert p2 in purchases
        assert p3 in purchases
        assert p1 not in purchases

        # Test date_before filter (line 43)
        response = client.get(url, {"date_before": "2024-02-28"})
        assert response.status_code == 200
        purchases = list(response.context["purchases"])
        assert p1 in purchases
        assert p2 in purchases
        assert p3 not in purchases

    def test_create_view_get_context_no_post(self, client, django_user_model):
        """Test PurchaseCreateView GET context (line 72)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse("purchases:create")
        response = client.get(url)

        assert response.status_code == 200
        assert "items" in response.context
        # Line 72: context["items"] = PurchaseItemFormSet()
        assert response.context["items"].instance.pk is None

    def test_create_view_service_exception(self, client, django_user_model):
        """Test PurchaseCreateView exception handling (lines 79-85)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner, is_supplier=True)

        url = reverse("purchases:create")
        data = {
            "date": "2024-01-01",
            "partner": partner.pk,
            "notes": "Test",
            "items-TOTAL_FORMS": "0",  # No items needed for form to be valid
            "items-INITIAL_FORMS": "0",
        }

        # Mock service to raise exception and verify handling
        verify_post_with_mocked_exception(
            client,
            url,
            data,
            "apps.purchases.services.purchase_service.PurchaseService.create_purchase_from_forms",
            Exception("Service Error"),
        )

    def test_create_view_success(self, client, django_user_model):
        """Test PurchaseCreateView success path (line 81)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner, is_supplier=True)

        url = reverse("purchases:create")
        data = {
            "date": "2024-01-01",
            "partner": partner.pk,
            "notes": "Test",
            "items-TOTAL_FORMS": "0",
            "items-INITIAL_FORMS": "0",
        }

        response = client.post(url, data)

        # Should redirect to list (line 81: return super().form_valid(form))
        assert response.status_code == 302
        assert Purchase.objects.count() == 1

    def test_update_view_get_context_no_post(self, client, django_user_model):
        """Test PurchaseUpdateView GET context (line 104)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        purchase = baker.make(Purchase)

        url = reverse("purchases:update", kwargs={"pk": purchase.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert "items" in response.context
        # Line 104: context["items"] = PurchaseItemFormSet(instance=self.object)
        assert response.context["items"].instance == purchase

    def test_update_view_form_invalid_items(self, client, django_user_model):
        """Test PurchaseUpdateView when items formset is invalid (line 127)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make(Partner, is_supplier=True)
        purchase = baker.make(Purchase, partner=partner)

        url = reverse("purchases:update", kwargs={"pk": purchase.pk})
        data = {
            "date": "2024-01-01",
            "partner": partner.pk,
            "notes": "Valid",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            # Invalid item data (negative quantity)
            "items-0-quantity": -1,
            "items-0-unit_price": "100.00",
        }

        response = client.post(url, data)
        assert response.status_code == 200
        # Line 127: return self.form_invalid(form)
        assert "items" in response.context
        assert response.context["items"].errors
