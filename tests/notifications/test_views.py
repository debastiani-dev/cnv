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

    def test_search_filtering(self):
        """Test search query parameter (lines 19-23)."""
        self.client.force_login(self.user)

        n1 = baker.make(Notification, recipient=self.user, title="Urgent Alert")
        n2 = baker.make(Notification, recipient=self.user, title="Regular Update")

        response = self.client.get(self.url + "?q=Urgent")

        assert n1 in response.context["notifications"]
        assert n2 not in response.context["notifications"]

    def test_category_filtering(self):
        """Test category query parameter (lines 26-28)."""
        self.client.force_login(self.user)

        n_info = baker.make(
            Notification, recipient=self.user, category=Notification.Category.INFO
        )
        n_alert = baker.make(
            Notification, recipient=self.user, category=Notification.Category.ALERT
        )

        response = self.client.get(self.url + f"?category={Notification.Category.INFO}")

        assert n_info in response.context["notifications"]
        assert n_alert not in response.context["notifications"]

    def test_status_filtering(self):
        """Test status (read/unread) query parameter (lines 31-35)."""
        self.client.force_login(self.user)

        n_read = baker.make(Notification, recipient=self.user, is_read=True)
        n_unread = baker.make(Notification, recipient=self.user, is_read=False)

        # Test Unread
        response = self.client.get(self.url + "?status=unread")
        assert n_unread in response.context["notifications"]
        assert n_read not in response.context["notifications"]

        # Test Read
        response = self.client.get(self.url + "?status=read")
        assert n_read in response.context["notifications"]
        assert n_unread not in response.context["notifications"]

    def test_context_data_filtering(self):
        """Test context data population (lines 42-47)."""
        self.client.force_login(self.user)

        url = self.url + f"?category={Notification.Category.INFO}&status=unread"
        response = self.client.get(url)

        assert response.status_code == 200
        assert "category_choices" in response.context
        assert response.context["selected_category"] == Notification.Category.INFO
        assert response.context["selected_status"] == "unread"
