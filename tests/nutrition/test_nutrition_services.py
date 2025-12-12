# pylint: disable=unused-argument
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.locations.models.location import Location
from apps.nutrition.models.diet import Diet, DietItem
from apps.nutrition.models.ingredient import FeedIngredient
from apps.nutrition.services.feeding_service import FeedingService


@pytest.mark.django_db
class TestFeedingService:
    @pytest.fixture
    def setup_data(self):
        self.corn = FeedIngredient.objects.create(
            name="Corn", stock_quantity=100.00, unit_cost=1.00
        )
        self.soy = FeedIngredient.objects.create(
            name="Soy", stock_quantity=50.00, unit_cost=2.00
        )
        self.diet = Diet.objects.create(name="Corn-Soy Mix")

        # 50% Corn, 50% Soy
        DietItem.objects.create(
            diet=self.diet, ingredient=self.corn, proportion_percent=50
        )
        DietItem.objects.create(
            diet=self.diet, ingredient=self.soy, proportion_percent=50
        )

        self.location = Location.objects.create(
            name="Test Paddock", capacity_head=10, area_hectares=10.0
        )

    def test_record_feeding_success(self, setup_data):
        # Feed 10kg Total: requires 5kg Corn, 5kg Soy
        # Cost: (5 * 1.00) + (5 * 2.00) = 5.00 + 10.00 = 15.00

        event = FeedingService.record_feeding(
            location=self.location,
            diet=self.diet,
            amount_kg=Decimal(10),
            date="2023-01-01",
            performed_by=None,
        )

        assert event.cost_total == Decimal("15.00")
        assert event.amount_kg == Decimal("10.00")

        self.corn.refresh_from_db()
        self.soy.refresh_from_db()

        assert self.corn.stock_quantity == Decimal("95.00")  # 100 - 5
        assert self.soy.stock_quantity == Decimal("45.00")  # 50 - 5

    def test_insufficient_stock(self, setup_data):
        # Feed 200kg Total: requires 100kg Corn (OK), 100kg Soy (Fail, only 50 available)

        with pytest.raises(ValidationError) as exc:
            FeedingService.record_feeding(
                location=self.location,
                diet=self.diet,
                amount_kg=Decimal(200),
                date="2023-01-01",
                performed_by=None,
            )

        assert "Insufficient stock for Soy" in str(exc.value)

        # Verify no changes
        self.corn.refresh_from_db()
        assert self.corn.stock_quantity == Decimal("100.00")

    def test_empty_diet_validation(self):
        empty_diet = Diet.objects.create(name="Empty")
        location = Location.objects.create(
            name="Loc", capacity_head=1, area_hectares=1.0
        )

        with pytest.raises(ValidationError) as exc:
            FeedingService.record_feeding(
                location=location,
                diet=empty_diet,
                amount_kg=Decimal(10),
                date="2023-01-01",
                performed_by=None,
            )
        assert "Selected diet has no ingredients" in str(exc.value)

    def test_negative_amount(self, setup_data):
        with pytest.raises(ValidationError):
            FeedingService.record_feeding(
                location=self.location,
                diet=self.diet,
                amount_kg=Decimal(-10),
                date="2023-01-01",
                performed_by=None,
            )
