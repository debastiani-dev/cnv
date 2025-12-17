from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.health.models.health import (
    ActiveIngredient,
    Medication,
    SanitaryEvent,
    SanitaryEventTarget,
)
from apps.health.services.health_service import HealthService


@pytest.mark.django_db
class TestHealthCompliance:
    def test_active_ingredient_reporting(self):
        # 1. Setup
        active_ing = baker.make(ActiveIngredient, name="Ivermectin")

        # Brand A: Ivomec (Linked to Ivermectin)
        med_a = baker.make(Medication, name="Ivomec Gold", withdrawal_days_meat=30)
        med_a.active_ingredients.add(active_ing)

        cow = baker.make(Cattle)

        # 2. Treat with Brand A 10 days ago (Still in withdrawal)
        event_date = timezone.now().date() - timedelta(days=10)
        event = baker.make(SanitaryEvent, medication=med_a, date=event_date)
        baker.make(SanitaryEventTarget, event=event, animal=cow)

        # 3. Check Withdrawal Status
        is_blocked, reason = HealthService.check_withdrawal_status(cow)

        # 4. Verify
        assert is_blocked is True
        assert "Active Ingredients: Ivermectin" in reason
        assert "Medication: Ivomec Gold" in reason

    def test_overlapping_ingredients(self):
        active_ing = baker.make(ActiveIngredient, name="Fipronil")

        med_a = baker.make(Medication, name="Brand A", withdrawal_days_meat=30)
        med_a.active_ingredients.add(active_ing)

        med_b = baker.make(Medication, name="Brand B", withdrawal_days_meat=30)
        med_b.active_ingredients.add(active_ing)

        cow = baker.make(Cattle)

        # Treat with A (20 days ago)
        baker.make(
            SanitaryEventTarget,
            event=baker.make(
                SanitaryEvent,
                medication=med_a,
                date=timezone.now().date() - timedelta(days=20),
            ),
            animal=cow,
        )

        # Treat with B (Today)
        baker.make(
            SanitaryEventTarget,
            event=baker.make(
                SanitaryEvent, medication=med_b, date=timezone.now().date()
            ),
            animal=cow,
        )

        is_blocked, reason = HealthService.check_withdrawal_status(cow)

        assert is_blocked is True
        assert "Active Ingredients: Fipronil" in reason
        assert "Medication: Brand B" in reason

    def test_combo_drug_reporting(self):
        """
        Verify that a multi-ingredient drug reports all ingredients.
        """
        ing_1 = baker.make(ActiveIngredient, name="Ivermectin")
        ing_2 = baker.make(ActiveIngredient, name="Fluazuron")

        combo_med = baker.make(Medication, name="ComboPlus", withdrawal_days_meat=45)
        combo_med.active_ingredients.add(ing_1, ing_2)

        cow = baker.make(Cattle)
        baker.make(
            SanitaryEventTarget,
            event=baker.make(
                SanitaryEvent, medication=combo_med, date=timezone.now().date()
            ),
            animal=cow,
        )

        is_blocked, reason = HealthService.check_withdrawal_status(cow)

        assert is_blocked is True
        assert "Ivermectin" in reason
        assert "Fluazuron" in reason
