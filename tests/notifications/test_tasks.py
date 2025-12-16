from unittest.mock import patch

from apps.notifications.tasks import run_notification_scanners


def test_run_notification_scanners():
    """Test that the celery task triggers the management command."""
    with patch("apps.notifications.tasks.call_command") as mock_call:
        run_notification_scanners()
        mock_call.assert_called_once_with("scan_notifications")
