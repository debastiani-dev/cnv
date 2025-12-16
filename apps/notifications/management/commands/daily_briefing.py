from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tasks.models.tasks import Task


class Command(BaseCommand):
    help = "Sends a daily briefing email to users"

    def handle(self, *args, **options):
        today = timezone.now().date()
        user_model = get_user_model()

        # In real scenario, iterate per user. For simplicity, just sending to superusers or all staff.
        users = user_model.objects.filter(is_active=True, is_staff=True)

        for user in users:
            # Tasks due today
            tasks_today = Task.objects.filter(
                assigned_to=user, due_date=today, status__in=["PENDING", "IN_PROGRESS"]
            ).count()

            # Tasks overdue
            tasks_overdue = Task.objects.filter(
                assigned_to=user,
                due_date__lt=today,
                status__in=["PENDING", "IN_PROGRESS"],
            ).count()

            if tasks_today == 0 and tasks_overdue == 0:
                continue

            subject = f"Daily Briefing - {today.strftime('%Y-%m-%d')}"
            message = f"""Hello {user.username},

Here is your daily briefing:

Tasks Due Today: {tasks_today}
Overdue Tasks: {tasks_overdue}

Please check the dashboard for details: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'}

Best regards,
CNV System
"""
            try:
                # Using send_mail which uses EMAIL_BACKEND settings
                send_mail(
                    subject,
                    message,
                    (
                        settings.DEFAULT_FROM_EMAIL
                        if hasattr(settings, "DEFAULT_FROM_EMAIL")
                        else "noreply@cnv.com"
                    ),
                    [user.email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f"Sent briefing to {user.email}"))
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.stdout.write(
                    self.style.ERROR(f"Failed to send to {user.email}: {e}")
                )
