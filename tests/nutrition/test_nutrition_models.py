import pytest

from apps.locations.models.location import Location
from apps.nutrition.models.diet import Diet, DietItem
from apps.nutrition.models.event import FeedingEvent
from apps.nutrition.models.ingredient import FeedIngredient


@pytest.mark.django_db
class TestNutritionModels:
    def test_ingredient_str(self):
        ingredient = FeedIngredient.objects.create(
            name="Corn", stock_quantity=100.00, unit_cost=1.50
        )
        assert str(ingredient) == "Corn (100.0 kg)"

    def test_diet_str(self):
        diet = Diet.objects.create(name="Starter Ratio")
        assert str(diet) == "Starter Ratio"

    def test_diet_item_str(self):
        diet = Diet.objects.create(name="Test Diet")
        ingredient = FeedIngredient.objects.create(name="Soy", stock_quantity=50)
        item = DietItem.objects.create(
            diet=diet, ingredient=ingredient, proportion_percent=20
        )
        assert str(item) == "Soy (20%)"

    def test_feeding_event_str(self):
        diet = Diet.objects.create(name="Mix A")
        location = Location.objects.create(
            name="Pasture 1", capacity_head=10, area_hectares=10.0
        )
        event = FeedingEvent.objects.create(
            date="2023-01-01",
            location=location,
            diet=diet,
            amount_kg=100,
            cost_total=150,
        )
        assert str(event) == "2023-01-01 - Pasture 1 - Mix A"
