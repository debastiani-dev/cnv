from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase


class ScanNotificationsCommandTest(TestCase):
    @patch("apps.notifications.management.commands.scan_notifications.LowStockScanner")
    @patch("apps.notifications.management.commands.scan_notifications.TaskDueScanner")
    @patch(
        "apps.notifications.management.commands.scan_notifications.PregnancyCheckScanner"
    )
    def test_scan_notifications_command(self, mock_preg, mock_task, mock_low):
        """Test that the command triggers all scanners."""
        # Setup mocks
        mock_low_instance = mock_low.return_value
        mock_low_instance.scan.return_value = 5  # Created 5 alerts
        mock_low_instance.__class__.__name__ = "LowStockScanner"

        mock_task_instance = mock_task.return_value
        mock_task_instance.scan.return_value = 0
        mock_task_instance.__class__.__name__ = "TaskDueScanner"

        mock_preg_instance = mock_preg.return_value
        mock_preg_instance.scan.return_value = 2
        mock_preg_instance.__class__.__name__ = "PregnancyCheckScanner"

        out = StringIO()
        call_command("scan_notifications", stdout=out)

        output = out.getvalue()

        # Verify calls
        assert mock_low.called
        mock_low_instance.scan.assert_called_once()

        assert mock_task.called
        mock_task_instance.scan.assert_called_once()

        assert mock_preg.called
        mock_preg_instance.scan.assert_called_once()

        # Verify Output
        assert "LowStockScanner: Created 5 notifications." in output
        assert "PregnancyCheckScanner: Created 2 notifications." in output
        assert "Total notifications created: 7" in output

    @patch("apps.notifications.management.commands.scan_notifications.LowStockScanner")
    def test_scan_notifications_error_handling(self, mock_low):
        """Test that errors in one scanner don't stop others."""
        mock_low_instance = mock_low.return_value
        mock_low_instance.scan.side_effect = Exception("Boom!")
        mock_low_instance.__class__.__name__ = "LowStockScanner"

        out = StringIO()
        call_command("scan_notifications", stdout=out)
        output = out.getvalue()

        assert "Error running LowStockScanner: Boom!" in output
