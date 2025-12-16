from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.notifications.models import Notification


class NotificationApiTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="apiuser", password="password"
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            title="API Test",
            message="Testing API",
        )
        self.url_list = reverse("notifications:api-list")

    def test_list_notifications_unauthenticated(self):
        response = self.client.get(self.url_list)
        self.assertNotEqual(response.status_code, 200)  # Should redirect to login

    def test_list_notifications_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url_list)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["unread_count"], 1)
        self.assertEqual(len(data["notifications"]), 1)
        self.assertEqual(data["notifications"][0]["title"], "API Test")

    def test_mark_read(self):
        self.client.force_login(self.user)
        url = reverse(
            "notifications:api-mark-read", kwargs={"pk": self.notification.pk}
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_mark_all_read(self):
        self.client.force_login(self.user)
        # Create another unread notification
        Notification.objects.create(recipient=self.user, title="Second")

        url = reverse("notifications:api-mark-all-read")
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Notification.objects.filter(recipient=self.user, is_read=False).exists()
        )
