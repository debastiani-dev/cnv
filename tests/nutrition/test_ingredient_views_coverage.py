from unittest.mock import patch

import pytest
from django.db.models import ProtectedError
from django.urls import reverse
from model_bakery import baker

from apps.nutrition.models import FeedIngredient


@pytest.mark.django_db
class TestIngredientViewsCoverage:

    def test_list_view_search(self, client, django_user_model):
        """Test search query filtering in IngredientListView."""
        user = baker.make(django_user_model)
        client.force_login(user)

        ing1 = baker.make(FeedIngredient, name="Corn Silage")
        ing2 = baker.make(FeedIngredient, name="Soybean Meal")

        url = reverse("nutrition:ingredient-list")

        response = client.get(url, {"q": "Corn"})
        assert ing1 in response.context["ingredients"]
        assert ing2 not in response.context["ingredients"]

    def test_restore_view_post_exception(self, client, django_user_model):
        """Test restore view POST DoesNotExist exception."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "nutrition:ingredient-restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        # Should redirect to list with error message
        assert response.status_code == 302
        assert response.url == reverse("nutrition:ingredient-list")

    def test_restore_view_get_exception(self, client, django_user_model):
        """Test restore view GET DoesNotExist exception."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "nutrition:ingredient-restore",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("nutrition:ingredient-list")

    def test_permanent_delete_view_post_does_not_exist(self, client, django_user_model):
        """Test permanent delete POST DoesNotExist exception."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "nutrition:ingredient-hard-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("nutrition:ingredient-trash")

    def test_permanent_delete_view_post_protected_error(
        self, client, django_user_model
    ):
        """Test permanent delete POST ProtectedError handling."""
        user = baker.make(django_user_model)
        client.force_login(user)
        ing = baker.make(FeedIngredient)
        ing.delete()

        url = reverse("nutrition:ingredient-hard-delete", kwargs={"pk": ing.pk})

        # Mock service to raise ProtectedError
        with patch(
            "apps.nutrition.services.IngredientService.hard_delete_ingredient",
            side_effect=ProtectedError("Protected", []),
        ):
            with patch(
                "apps.nutrition.models.FeedIngredient.all_objects.get", return_value=ing
            ):
                response = client.post(url)
                # Should render confirmation page with error
                assert response.status_code == 200
                assert "error" in response.context
                assert response.context["ingredient"] == ing

    def test_permanent_delete_view_post_protected_error_obj_missing(
        self, client, django_user_model
    ):
        """Test permanent delete POST ProtectedError but object vanished (race condition)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        ing = baker.make(FeedIngredient)
        ing.delete()

        url = reverse("nutrition:ingredient-hard-delete", kwargs={"pk": ing.pk})

        # Mock service to raise ProtectedError
        with patch(
            "apps.nutrition.services.IngredientService.hard_delete_ingredient",
            side_effect=ProtectedError("Protected", []),
        ):
            # Mock get to raise DoesNotExist (simulating it disappeared during handling)
            with patch(
                "apps.nutrition.models.FeedIngredient.all_objects.get",
                side_effect=FeedIngredient.DoesNotExist,
            ):
                response = client.post(url)
                # Should redirect to trash
                assert response.status_code == 302
                assert response.url == reverse("nutrition:ingredient-trash")

    def test_permanent_delete_view_get_exception(self, client, django_user_model):
        """Test permanent delete GET DoesNotExist exception."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse(
            "nutrition:ingredient-hard-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("nutrition:ingredient-trash")
