from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# Import Scanners to avoid duplication
from apps.notifications.services.scanners.low_stock import LowStockScanner
from apps.notifications.services.scanners.pregnancy_check import PregnancyCheckScanner
from apps.notifications.services.scanners.task_due import TaskDueScanner

# Import models
from apps.nutrition.models.event import FeedingEvent
from apps.reproduction.models.reproduction import BreedingEvent
from apps.tasks.models.tasks import Task

# RainfallEntry not found, skipping Weather listener for now
# from apps.locations.models import RainfallEntry


@receiver(post_save, sender=FeedingEvent)
def check_stock_level(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
    """
    Check if ingredient stock is low after a feeding event.
    Ref: apps.nutrition.models.event.FeedingEvent
    """
    if not created:
        return

    # Check stock for ingredients in the diet
    diet = instance.diet
    scanner = LowStockScanner()

    for item in diet.items.all():
        ingredient = item.ingredient
        # Explicit check logic is duplicated from scanner query, but that's fine.
        if ingredient.stock_quantity < ingredient.min_stock_alert:
            scanner.check_ingredient(ingredient)


@receiver(post_save, sender=BreedingEvent)
def schedule_pregnancy_check_reminder(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
    """
    Check if a pregnancy check reminder is needed.
    """
    if not created:
        return

    # Logic: If event date was 30 days ago, remind.
    # Note: This logic for "should we check" needs to be consistent.
    # The scan query checks for "30+ days ago".
    # Here we check if `instance.date` matches specific condition?
    # Original listener checked "diff >= 30".

    days_diff = (timezone.now().date() - instance.date).days
    # If exactly 30 days or more (backdated entry)
    if days_diff >= 30 and not instance.pregnancy_checks.exists():
        PregnancyCheckScanner().check_event(instance)


@receiver(post_save, sender=Task)
def task_due_reminder(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
    """
    Notify assigned user when a task is created due today.
    """
    if instance.due_date == timezone.now().date() and instance.assigned_to:
        # Note: Scanner checks for "Pending" status and assigned_to.
        # We assume if it's Just Created, it's Pending.
        TaskDueScanner().check_task(instance)
