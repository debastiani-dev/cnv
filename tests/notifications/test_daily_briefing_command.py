from datetime import timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from model_bakery import baker

from apps.authentication.models import User
from apps.tasks.models.tasks import Task


@pytest.mark.django_db
class TestDailyBriefingCommand:
    def test_no_tasks_no_email(self):
        """Test that no email is sent if there are no relevant tasks."""
        # Setup: Staff user but no tasks
        baker.make(User, is_staff=True, is_active=True, email="staff@example.com")

        with patch(
            "apps.notifications.management.commands.daily_briefing.send_mail"
        ) as mock_send:
            out = StringIO()
            call_command("daily_briefing", stdout=out)
            mock_send.assert_not_called()
            # Nothing in stdout about sending
            assert "Sent briefing" not in out.getvalue()

    def test_daily_briefing_sends_email(self):
        """Test that email is sent when tasks are due or overdue."""
        user = baker.make(User, is_staff=True, is_active=True, email="boss@example.com")
        today = timezone.now().date()

        # 1 Due Today
        baker.make(Task, assigned_to=user, due_date=today, status="PENDING")
        # 1 Overdue
        baker.make(
            Task,
            assigned_to=user,
            due_date=today - timedelta(days=1),
            status="IN_PROGRESS",
        )
        # 1 Future (Ignore)
        baker.make(
            Task, assigned_to=user, due_date=today + timedelta(days=1), status="PENDING"
        )

        with patch(
            "apps.notifications.management.commands.daily_briefing.send_mail"
        ) as mock_send:
            out = StringIO()
            call_command("daily_briefing", stdout=out)

            mock_send.assert_called_once()
            args = mock_send.call_args[0]
            subject, message = args[0], args[1]

            assert "Daily Briefing" in subject
            assert "Tasks Due Today: 1" in message
            assert "Overdue Tasks: 1" in message
            assert "sent briefing to boss@example.com" in out.getvalue().lower()

    def test_email_error_handling(self):
        """Test that email sending errors are logged."""
        user = baker.make(
            User, is_staff=True, is_active=True, email="error@example.com"
        )
        today = timezone.now().date()
        baker.make(Task, assigned_to=user, due_date=today, status="PENDING")

        with patch(
            "apps.notifications.management.commands.daily_briefing.send_mail"
        ) as mock_send:
            mock_send.side_effect = Exception("SMTP Down")

            out = StringIO()
            call_command("daily_briefing", stdout=out)

            output = out.getvalue()
            assert "Failed to send to error@example.com: SMTP Down" in output
