import uuid
from io import StringIO

import pytest
from django.core.management import call_command
from model_bakery import baker

from apps.notifications.models import Notification


@pytest.mark.django_db
class TestFixNotificationLinksCommand:
    def test_fix_links_updates_records(self):
        """Test that the command updates broken breeding links."""
        # Setup: 1 Broken, 1 Valid, 1 Unrelated
        uid = str(uuid.uuid4())
        bad = baker.make(Notification, link=f"/reproduction/breeding/{uid}/")
        good = baker.make(Notification, link="/reproduction/breeding/")
        other = baker.make(Notification, link="/tasks/123/")

        out = StringIO()
        call_command("fix_notification_links", stdout=out)

        output = out.getvalue()
        assert "Fixed 1 broken breeding links" in output

        # Verify DB updates
        bad.refresh_from_db()
        assert bad.link == "/reproduction/breeding/"

        good.refresh_from_db()
        assert good.link == "/reproduction/breeding/"

        other.refresh_from_db()
        assert other.link == "/tasks/123/"

    def test_no_broken_links(self):
        """Test execution when nothing needs fixing."""
        baker.make(Notification, link="/reproduction/breeding/")

        out = StringIO()
        call_command("fix_notification_links", stdout=out)

        output = out.getvalue()
        assert "Fixed 0 broken breeding links" in output
