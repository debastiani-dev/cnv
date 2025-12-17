from decimal import Decimal

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.authentication.models import User
from apps.notifications.models.notification import Notification
from apps.nutrition.models.diet import Diet, DietItem
from apps.nutrition.models.ingredient import FeedIngredient
from apps.nutrition.services.feeding_service import FeedingService
from apps.tasks.models.tasks import Task


@pytest.mark.django_db
class TestInventorySoftBlock:
    def test_negative_stock_flow(self):
        # 1. Setup
        user = baker.make(User, username="feeder_guy")
        location = baker.make("locations.Location", name="Paddock A")

        # Ingredient with low stock
        corn = baker.make(
            FeedIngredient,
            name="Corn",
            stock_quantity=Decimal("100.00"),
            unit_cost=Decimal("1.00"),
        )

        # Diet: 100% Corn
        diet = baker.make(Diet, name="Pure Corn Diet")
        baker.make(
            DietItem, diet=diet, ingredient=corn, proportion_percent=Decimal("100.00")
        )

        # 2. Execute: Feed more than available (150kg needed, 100kg available)
        # Should NOT raise ValidationError anymore
        FeedingService.record_feeding(
            location=location,
            diet=diet,
            amount_kg=Decimal("150.00"),
            date=timezone.now().date(),
            performed_by=user,
        )

        # 3. Verify
        corn.refresh_from_db()
        assert corn.stock_quantity == Decimal(
            "-50.00"
        ), "Stock should be allowed to go negative"

        # Check Notification
        assert Notification.objects.filter(recipient=user, category="ALERT").exists()
        notif = Notification.objects.last()
        assert "Negative Inventory: Corn" in notif.title
        assert "-50.00kg" in notif.message

        # Check Task
        assert Task.objects.filter(title="Audit Inventory: Corn").exists()
        task = Task.objects.get(title="Audit Inventory: Corn")
        assert task.priority == "HIGH"
        assert task.assigned_to == user
