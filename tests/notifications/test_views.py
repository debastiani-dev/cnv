from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from model_bakery import baker

from apps.notifications.models import Notification

User = get_user_model()


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
)
class TestNotificationListView(TestCase):
    def setUp(self):
        self.url = reverse("notifications:list")
        self.user = baker.make(User)

    def test_login_required(self):
        response = self.client.get(self.url)
        assert response.status_code == 302  # Redirection to login

    def test_list_view_context(self):
        self.client.force_login(self.user)
        # Create notifications for user
        baker.make(Notification, recipient=self.user, _quantity=3)
        # Create notification for another user
        other_user = baker.make(User)
        baker.make(Notification, recipient=other_user)

        response = self.client.get(self.url)

        assert response.status_code == 200
        assert len(response.context["notifications"]) == 3
        # Ensure only user's notifications are shown
        for n in response.context["notifications"]:
            assert n.recipient == self.user
