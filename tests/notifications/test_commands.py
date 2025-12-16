from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from model_bakery import baker

from apps.notifications.models import Notification
from apps.reproduction.models import BreedingEvent
from apps.tasks.models import Task

User = get_user_model()


@pytest.mark.django_db
class TestDailyBriefingCommand:
    def test_daily_briefing_sends_email(self):
        user = baker.make(User, is_staff=True, email="staff@example.com")
        today = timezone.now().date()

        # Create tasks
        baker.make(Task, assigned_to=user, due_date=today, status="PENDING")

        out = StringIO()
        call_command("daily_briefing", stdout=out)

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]
        assert "Daily Briefing" in mail.outbox[0].subject
        assert "sent briefing" in out.getvalue().lower()

    def test_daily_briefing_skips_if_no_tasks(self):
        baker.make(User, is_staff=True, email="staff@example.com")
        # No tasks

        out = StringIO()
        call_command("daily_briefing", stdout=out)

        assert len(mail.outbox) == 0

    def test_daily_briefing_exception(self):
        """Test exception handling during email sending."""
        user = baker.make(User, is_staff=True, email="fail@example.com")
        today = timezone.now().date()
        baker.make(Task, assigned_to=user, due_date=today, status="PENDING")

        out = StringIO()
        with patch(
            "apps.notifications.management.commands.daily_briefing.send_mail",
            side_effect=Exception("SMTP Error"),
        ):
            call_command("daily_briefing", stdout=out)

        assert "Failed to send" in out.getvalue()


@pytest.mark.django_db
class TestCheckRemindersCommand:
    def test_check_reminders_creates_notifications(self):
        staff = baker.make(User, is_staff=True)
        # 30 days ago
        date_30_days_ago = timezone.now().date() - timezone.timedelta(days=30)

        # Event needing check
        baker.make(BreedingEvent, date=date_30_days_ago, dam__tag="TESTCOW")

        out = StringIO()
        call_command("check_reminders", stdout=out)

        assert Notification.objects.filter(
            recipient=staff, title="Pregnancy Check Due"
        ).exists()
        assert "Created" in out.getvalue()

    def test_check_reminders_no_events(self):
        """Test when there are no events to check."""
        out = StringIO()
        call_command("check_reminders", stdout=out)
        assert "No pending pregnancy checks found" in out.getvalue()
