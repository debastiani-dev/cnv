import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from model_bakery import baker

from apps.notifications.models import Notification
from apps.nutrition.models import FeedingEvent
from apps.reproduction.models import BreedingEvent
from apps.tasks.models import Task

User = get_user_model()


@pytest.mark.django_db
class TestNotificationListeners:
    def test_stock_alert_listener(self):
        """Test that a stock alert is created when ingredient stock is low."""
        user = baker.make(User, is_staff=True)
        # Create ingredient with low stock threshold
        ingredient = baker.make(
            "nutrition.FeedIngredient",
            name="Corn",
            stock_quantity=100,
            min_stock_alert=50,
        )
        diet = baker.make("nutrition.Diet")
        baker.make("nutrition.DietItem", diet=diet, ingredient=ingredient)

        # Create feeding event that reduces stock below threshold
        # Note: The listener assumes stock is ALREADY deducted.
        # So we manually set stock low to simulate the condition the listener checks.
        ingredient.stock_quantity = 40
        ingredient.save()

        baker.make(
            FeedingEvent, diet=diet, performed_by=user, date=timezone.now().date()
        )

        # Check notification created
        assert Notification.objects.filter(
            recipient=user,
            category=Notification.Category.ALERT,
            title="Low Stock Alert",
        ).exists()

    def test_stock_alert_fallback_recipient(self):
        """Test fallback to staff users when performed_by is missing."""
        staff_user = baker.make(User, is_staff=True, is_active=True)
        # Create ingredient with low stock
        ingredient = baker.make(
            "nutrition.FeedIngredient", stock_quantity=10, min_stock_alert=50
        )
        diet = baker.make("nutrition.Diet")
        baker.make("nutrition.DietItem", diet=diet, ingredient=ingredient)

        # Create feeding event without performed_by
        baker.make(
            FeedingEvent, diet=diet, performed_by=None, date=timezone.now().date()
        )

        # Check notification sent to staff
        assert Notification.objects.filter(
            recipient=staff_user, category=Notification.Category.ALERT
        ).exists()

    def test_stock_alert_update_ignored(self):
        """Test that the listener ignores updates (only runs on creation)."""
        user = baker.make(User)
        ingredient = baker.make(
            "nutrition.FeedIngredient", stock_quantity=10, min_stock_alert=50
        )
        diet = baker.make("nutrition.Diet")
        baker.make("nutrition.DietItem", diet=diet, ingredient=ingredient)

        # Create initial event (triggers logic)
        event = baker.make(
            FeedingEvent, diet=diet, performed_by=user, date=timezone.now().date()
        )
        Notification.objects.all().delete()  # Clear notifications

        # Update event (sends signal with created=False)
        event.save()

        # Assert no new notification
        assert not Notification.objects.exists()

    def test_pregnancy_check_reminder_listener(self):
        """Test pregnancy check reminder for backdated breeding events."""
        staff_user = baker.make(User, is_staff=True, is_active=True)

        # Create a breeding event 30 days ago
        date_30_days_ago = timezone.now().date() - timezone.timedelta(days=30)

        baker.make(BreedingEvent, date=date_30_days_ago, dam__tag="COW001")

        # Listener runs on save, so creating it should trigger logic
        # Check notification sent to staff
        assert Notification.objects.filter(
            recipient=staff_user,
            category=Notification.Category.REMINDER,
            title="Pregnancy Check Due",
        ).exists()

    def test_task_due_reminder_listener(self):
        """Test task due notification."""
        user = baker.make(User)
        today = timezone.now().date()

        baker.make(Task, assigned_to=user, due_date=today, title="Fix Fence")

        assert Notification.objects.filter(
            recipient=user,
            category=Notification.Category.REMINDER,
            title="Task Due",
        ).exists()
