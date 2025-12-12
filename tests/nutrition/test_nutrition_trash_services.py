import pytest

from apps.nutrition.models import Diet, FeedIngredient
from apps.nutrition.services import DietService, IngredientService


@pytest.mark.django_db
class TestIngredientServiceTrash:
    @pytest.fixture
    def deleted_ingredient(self):
        ingredient = FeedIngredient.objects.create(
            name="Deleted Corn", stock_quantity=10, unit_cost=1, min_stock_alert=5
        )
        ingredient.delete()  # Soft delete
        return ingredient

    def test_get_deleted_ingredients(self, deleted_ingredient):
        # Create active one to ensure it's not returned
        FeedIngredient.objects.create(
            name="Active Corn", stock_quantity=10, unit_cost=1
        )

        deleted = IngredientService.get_deleted_ingredients()
        assert deleted.count() == 1
        assert deleted.first().pk == deleted_ingredient.pk

    def test_restore_ingredient(self, deleted_ingredient):
        restored = IngredientService.restore_ingredient(deleted_ingredient.pk)

        # Verify it's active
        assert restored.is_deleted is False

        refreshed = FeedIngredient.objects.get(pk=deleted_ingredient.pk)
        assert refreshed.is_deleted is False

        # Verify it's not in deleted list
        assert IngredientService.get_deleted_ingredients().count() == 0

    def test_hard_delete_ingredient(self, deleted_ingredient):
        IngredientService.hard_delete_ingredient(deleted_ingredient.pk)

        # Verify it's gone from DB completely
        assert (
            FeedIngredient.all_objects.filter(pk=deleted_ingredient.pk).exists()
            is False
        )


@pytest.mark.django_db
class TestDietServiceTrash:
    @pytest.fixture
    def deleted_diet(self):
        diet = Diet.objects.create(name="Deleted Diet")
        diet.delete()  # Soft delete
        return diet

    def test_get_deleted_diets(self, deleted_diet):
        # Create active one
        Diet.objects.create(name="Active Diet")

        deleted = DietService.get_deleted_diets()
        assert deleted.count() == 1
        assert deleted.first().pk == deleted_diet.pk

    def test_restore_diet(self, deleted_diet):
        restored = DietService.restore_diet(deleted_diet.pk)

        assert restored.is_deleted is False

        refreshed = Diet.objects.get(pk=deleted_diet.pk)
        assert refreshed.is_deleted is False

    def test_hard_delete_diet(self, deleted_diet):
        DietService.hard_delete_diet(deleted_diet.pk)

        assert Diet.all_objects.filter(pk=deleted_diet.pk).exists() is False
