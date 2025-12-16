from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models.notification import Notification
from apps.notifications.services.notification_service import create_notification
from apps.reproduction.models.reproduction import BreedingEvent


class Command(BaseCommand):
    help = "Checks for missing pregnancy checks 30 days after breeding"

    def handle(self, *args, **options):
        # 30 days ago
        target_date = timezone.now().date() - timezone.timedelta(days=30)

        # Find events on that date without pregnancy checks
        events = BreedingEvent.objects.filter(date=target_date).exclude(
            pregnancy_checks__isnull=False
        )

        if not events.exists():
            self.stdout.write("No pending pregnancy checks found for today.")
            return

        user_model = get_user_model()
        # Notify admins/staff
        recipients = user_model.objects.filter(is_active=True, is_staff=True)

        count = 0
        for event in events:
            for recipient in recipients:
                create_notification(
                    recipient=recipient,
                    title="Pregnancy Check Due",
                    message=f"Breeding event for {event.dam} on {event.date} needs a pregnancy check.",
                    category=Notification.Category.REMINDER,
                    link="/reproduction/breeding/",  # Hypothetical link
                )
            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {count} notifications for missing pregnancy checks."
            )
        )
