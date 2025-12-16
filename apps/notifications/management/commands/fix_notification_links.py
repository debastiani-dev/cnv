from django.core.management.base import BaseCommand

from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Fixes broken notification links retroactively."

    def handle(self, *args, **options):
        # Fix Breeding Links
        broken_breeding = Notification.objects.filter(
            link__regex=r"^/reproduction/breeding/[0-9a-f-]{36}/$"
        )
        count = broken_breeding.update(link="/reproduction/breeding/")
        self.stdout.write(self.style.SUCCESS(f"Fixed {count} broken breeding links."))
