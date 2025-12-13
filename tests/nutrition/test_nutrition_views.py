# pylint: disable=unused-argument, redefined-outer-name
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.authentication.models import User
from apps.locations.models.location import Location
from apps.nutrition.models import Diet, FeedingEvent, FeedIngredient
from tests.test_utils import verify_protected_error_response


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="password")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.mark.django_db
class TestIngredientViews:
    def test_list_view(self, auth_client):
        baker.make(FeedIngredient, name="Corn")
        url = reverse("nutrition:ingredient-list")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "ingredients" in response.context
        assert len(response.context["ingredients"]) == 1

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
        ingredient = baker.make(FeedIngredient, name="Old Name")
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

    def test_delete_view_get_confirmation(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        url = reverse("nutrition:ingredient-delete", kwargs={"pk": ingredient.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "delete" in response.content.decode().lower()

    def test_delete_view_post(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        url = reverse("nutrition:ingredient-delete", kwargs={"pk": ingredient.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert not FeedIngredient.objects.filter(pk=ingredient.pk).exists()
        assert FeedIngredient.all_objects.filter(
            pk=ingredient.pk, is_deleted=True
        ).exists()

    def test_trash_list_view(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        ingredient.delete()
        url = reverse("nutrition:ingredient-trash")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert ingredient in response.context["ingredients"]

    def test_restore_view_get_confirmation(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        ingredient.delete()
        url = reverse("nutrition:ingredient-restore", kwargs={"pk": ingredient.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "restore" in response.content.decode().lower()

    def test_restore_view_post(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        ingredient.delete()
        url = reverse("nutrition:ingredient-restore", kwargs={"pk": ingredient.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert FeedIngredient.objects.filter(pk=ingredient.pk).exists()

    def test_hard_delete_view_get_confirmation(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        ingredient.delete()
        url = reverse("nutrition:ingredient-hard-delete", kwargs={"pk": ingredient.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "permanently" in response.content.decode().lower()

    def test_hard_delete_view_post(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        ingredient.delete()
        url = reverse("nutrition:ingredient-hard-delete", kwargs={"pk": ingredient.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert not FeedIngredient.all_objects.filter(pk=ingredient.pk).exists()


@pytest.mark.django_db
class TestDietViews:
    def test_list_view(self, auth_client):
        baker.make(Diet, name="Test Diet")
        url = reverse("nutrition:diet-list")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "diets" in response.context

    def test_create_view(self, auth_client):
        ingredient = baker.make(FeedIngredient)
        url = reverse("nutrition:diet-create")
        data = {
            "name": "Growth Diet",
            "description": "Desc",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-ingredient": ingredient.pk,
            "items-0-proportion_percent": "50.00",
            "items-0-fixed_amount_kg": "",
        }
        response = auth_client.post(url, data)
        assert response.status_code == 302
        assert Diet.objects.filter(name="Growth Diet").exists()

    def test_delete_view_get_confirmation(self, auth_client):
        diet = baker.make(Diet)
        url = reverse("nutrition:diet-delete", kwargs={"pk": diet.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "delete" in response.content.decode().lower()

    def test_delete_view_post(self, auth_client):
        diet = baker.make(Diet)
        url = reverse("nutrition:diet-delete", kwargs={"pk": diet.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert not Diet.objects.filter(pk=diet.pk).exists()

    def test_trash_list_view(self, auth_client):
        diet = baker.make(Diet)
        diet.delete()
        url = reverse("nutrition:diet-trash")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert diet in response.context["diets"]

    def test_restore_view_get_confirmation(self, auth_client):
        diet = baker.make(Diet)
        diet.delete()
        url = reverse("nutrition:diet-restore", kwargs={"pk": diet.pk})
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_restore_view_post(self, auth_client):
        diet = baker.make(Diet)
        diet.delete()
        url = reverse("nutrition:diet-restore", kwargs={"pk": diet.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert Diet.objects.filter(pk=diet.pk).exists()

    def test_hard_delete_view_post(self, auth_client):
        diet = baker.make(Diet)
        diet.delete()
        url = reverse("nutrition:diet-hard-delete", kwargs={"pk": diet.pk})
        response = auth_client.post(url)
        assert response.status_code == 302
        assert not Diet.all_objects.filter(pk=diet.pk).exists()

    def test_list_search(self, auth_client):
        baker.make(Diet, name="Alpha")
        baker.make(Diet, name="Beta")
        url = reverse("nutrition:diet-list")
        response = auth_client.get(url, {"q": "Alpha"})
        assert len(response.context["diets"]) == 1
        assert response.context["diets"][0].name == "Alpha"

    def test_create_view_get(self, auth_client):
        url = reverse("nutrition:diet-create")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "items" in response.context  # Formset

    def test_create_view_invalid(self, auth_client):
        url = reverse("nutrition:diet-create")
        data = {
            "name": "Invalid Diet",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            # Missing ingredient
            "items-0-proportion_percent": "abc",  # Invalid
        }
        response = auth_client.post(url, data)
        assert response.status_code == 200
        assert not Diet.objects.filter(name="Invalid Diet").exists()

    def test_update_view_get(self, auth_client):
        diet = baker.make(Diet)
        baker.make("nutrition.DietItem", diet=diet)
        url = reverse("nutrition:diet-update", kwargs={"pk": diet.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "items" in response.context

    def test_update_view_post(self, auth_client):
        diet = baker.make(Diet, name="Old Name")
        item = baker.make("nutrition.DietItem", diet=diet, proportion_percent=10)
        url = reverse("nutrition:diet-update", kwargs={"pk": diet.pk})
        data = {
            "name": "New Name",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "1",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            "items-0-uuid": item.pk,
            "items-0-ingredient": item.ingredient.pk,
            "items-0-proportion_percent": "20.00",
            # "items-0-diet": diet.pk, # Should not be needed in POST if mapped correctly or logic handles it
        }
        response = auth_client.post(url, data)
        if response.status_code != 302:
            print(response.context["form"].errors)
            if "items" in response.context:
                print(response.context["items"].errors)
        assert response.status_code == 302
        diet.refresh_from_db()
        assert diet.name == "New Name"
        item.refresh_from_db()
        # Fix lint: floating point check
        assert item.proportion_percent == Decimal("20.00")

    def test_restore_not_found(self, auth_client):
        url = reverse("nutrition:diet-restore", kwargs={"pk": uuid.uuid4()})
        response_post = auth_client.post(url)
        assert response_post.status_code == 302

        response_get = auth_client.get(url)
        assert response_get.status_code == 302

    def test_hard_delete_not_found(self, auth_client):
        url = reverse("nutrition:diet-hard-delete", kwargs={"pk": uuid.uuid4()})
        response_post = auth_client.post(url)
        assert response_post.status_code == 302

        response_get = auth_client.get(url)
        assert response_get.status_code == 302

    def test_hard_delete_protected(self, auth_client):
        diet = baker.make(Diet)
        diet.delete()
        url = reverse("nutrition:diet-hard-delete", kwargs={"pk": diet.pk})

        with patch(
            "apps.nutrition.services.DietService.hard_delete_diet",
            side_effect=ProtectedError("Protected", []),
        ):
            verify_protected_error_response(auth_client, url, "cannot delete")

    def test_hard_delete_view_get_confirmation(self, auth_client):
        diet = baker.make(Diet)
        diet.delete()
        url = reverse("nutrition:diet-hard-delete", kwargs={"pk": diet.pk})
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "permanently" in response.content.decode().lower()


@pytest.mark.django_db
class TestFeedingEventViews:
    def test_list_view(self, auth_client):
        baker.make(FeedingEvent)
        url = reverse("nutrition:event-list")
        response = auth_client.get(url)
        assert response.status_code == 200
        assert "events" in response.context

    def test_create_view_success(self, auth_client):
        location = baker.make(Location)
        diet = baker.make(Diet)
        ingredient = baker.make(FeedIngredient, stock_quantity=1000)
        baker.make(
            "nutrition.DietItem",
            diet=diet,
            ingredient=ingredient,
            proportion_percent=100,
        )
        url = reverse("nutrition:event-create")
        data = {
            "date": "2024-01-01",
            "diet": diet.pk,
            "location": location.pk,
            "amount_kg": "500",
        }
        response = auth_client.post(url, data)
        if response.status_code != 302:
            print(response.content.decode())
            print(response.context["form"].errors)
        assert response.status_code == 302
        assert FeedingEvent.objects.exists()
