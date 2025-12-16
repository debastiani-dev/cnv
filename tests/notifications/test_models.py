from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.models import Notification
from apps.notifications.services.notification_service import create_notification


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", password="password"
        )

    def test_create_notification(self):
        notification = Notification.objects.create(
            recipient=self.user,
            title="Test Notification",
            message="This is a test",
            category=Notification.Category.INFO,
        )
        self.assertEqual(notification.title, "Test Notification")
        self.assertFalse(notification.is_read)
        self.assertEqual(
            str(notification), f"INFO: Test Notification ({self.user.username})"
        )

    def test_service_create_notification(self):
        notification = create_notification(
            recipient=self.user,
            title="Service Notification",
            message="Created via service",
        )
        self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())
        self.assertEqual(notification.category, Notification.Category.INFO)
