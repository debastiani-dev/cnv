# pylint: disable=redefined-outer-name
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.authentication.models import User
from apps.nutrition.models import Diet, FeedIngredient


@pytest.fixture
def auth_client(client):
    user = User.objects.create_user(username="testuser", password="password")
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestIngredientViews:
    def test_list_view(self, auth_client):
        url = reverse("nutrition:ingredient-list")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "ingredients" in response.context

    def test_create_view(self, auth_client):
        url = reverse("nutrition:ingredient-create")
        data = {
            "name": "New Ingredient",
            "stock_quantity": "100.00",
            "unit_cost": "1.50",
            "min_stock_alert": "10.00",
        }
        response = auth_client.post(url, data)
        assert response.status_code == 302
        assert FeedIngredient.objects.filter(name="New Ingredient").exists()

    def test_update_view(self, auth_client):
        ingredient = FeedIngredient.objects.create(
            name="Old Name", stock_quantity=10, unit_cost=1
        )
        url = reverse("nutrition:ingredient-update", kwargs={"pk": ingredient.pk})
        data = {
            "name": "Updated Name",
            "stock_quantity": "20.00",
            "unit_cost": "2.00",
            "min_stock_alert": "5.00",
        }
        response = auth_client.post(url, data)
        assert response.status_code == 302

        ingredient.refresh_from_db()
        assert ingredient.name == "Updated Name"
        assert ingredient.stock_quantity == Decimal("20.00")

    def test_delete_view_soft_delete(self, auth_client):
        ingredient = FeedIngredient.objects.create(
            name="To Delete", stock_quantity=10, unit_cost=1
        )
        url = reverse("nutrition:ingredient-delete", kwargs={"pk": ingredient.pk})

        # DeleteView usually requires POST to confirm deletion
        response = auth_client.post(url)
        assert response.status_code == 302

        ingredient.refresh_from_db()
        assert ingredient.is_deleted is True


@pytest.mark.django_db
class TestDietViews:
    def test_list_view(self, auth_client):
        url = reverse("nutrition:diet-list")
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_create_view_with_items(self, auth_client):
        ingredient = FeedIngredient.objects.create(
            name="Corn", stock_quantity=100, unit_cost=1
        )
        url = reverse("nutrition:diet-create")

        # Construct formset data
        data = {
            "name": "Growth Diet",
            "description": "For growing calves",
            # Management Form for Inline Formset
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            # Form 0
            "items-0-ingredient": ingredient.pk,
            "items-0-proportion_percent": "50.00",
            "items-0-fixed_amount_kg": "",
        }

        auth_client.post(url, data)

        # Check if saved
        assert Diet.objects.filter(name="Growth Diet").exists()
        diet = Diet.objects.get(name="Growth Diet")
        assert diet.items.count() == 1
        assert diet.items.first().ingredient == ingredient

    def test_delete_view_soft_delete(self, auth_client):
        diet = Diet.objects.create(name="Delete Me")
        url = reverse("nutrition:diet-delete", kwargs={"pk": diet.pk})

        response = auth_client.post(url)
        assert response.status_code == 302

        diet.refresh_from_db()
        assert diet.is_deleted is True
