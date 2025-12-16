from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.notifications.models import Notification
from apps.notifications.services.notification_service import create_notification

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

    # Algorithm:
    # Check if ingredient stock < min_stock_alert for any ingredient in the diet.

    diet = instance.diet

    for item in diet.items.all():
        ingredient = item.ingredient

        # Assumption: FeedingEvent processing ALREADY deducted the stock.
        # So current stock_quantity is the after-feeding value.
        if ingredient.stock_quantity < ingredient.min_stock_alert:
            recipients = [instance.performed_by] if instance.performed_by else []
            if not recipients:
                # Fallback to system admin or staff
                user_model = get_user_model()
                recipients = user_model.objects.filter(is_active=True, is_staff=True)

            for recipient in recipients:
                create_notification(
                    recipient=recipient,
                    title=_("Low Stock Alert"),
                    message=_(
                        "Stock for {ingredient} is low ({current}kg). Min threshold: {min}kg."
                    ).format(
                        ingredient=ingredient.name,
                        current=ingredient.stock_quantity,
                        min=ingredient.min_stock_alert,
                    ),
                    category=Notification.Category.ALERT,
                    link=f"/nutrition/ingredients/{ingredient.pk}/update/",
                )


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
    # Note: This listener runs on SAVE. So it catches backdated events.
    days_diff = (timezone.now().date() - instance.date).days

    # If exactly 30 days or more (backdated entry)
    if days_diff >= 30:
        if not instance.pregnancy_checks.exists():
            # Notify all staff users
            user_model = get_user_model()
            recipients = user_model.objects.filter(is_active=True, is_staff=True)
            for recipient in recipients:
                create_notification(
                    recipient=recipient,
                    title=_("Pregnancy Check Due"),
                    message=_(
                        "Breeding event for {dam} on {date} needs a pregnancy check."
                    ).format(dam=instance.dam, date=instance.date),
                    category=Notification.Category.REMINDER,
                    link=f"/reproduction/breeding/{instance.pk}/",
                )


@receiver(post_save, sender=Task)
def task_due_reminder(
    sender, instance, created, **kwargs
):  # pylint: disable=unused-argument
    """
    Notify assigned user when a task is created due today.
    """
    if instance.due_date == timezone.now().date() and instance.assigned_to:
        create_notification(
            recipient=instance.assigned_to,
            title=_("Task Due Today"),
            message=_("Task '{title}' is due today.").format(title=instance.title),
            category=Notification.Category.REMINDER,
            link=f"/tasks/{instance.pk}/",
        )
