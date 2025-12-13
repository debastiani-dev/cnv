from unittest.mock import patch

import pytest
from django.contrib.messages import get_messages
from django.db.models import ProtectedError
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.reproduction.models import ReproductiveSeason


@pytest.mark.django_db
class TestReproductiveSeasonViews:
    """Tests for ReproductiveSeason views."""

    def test_list_view(self, client, user):
        """Test list view with filters."""
        client.force_login(user)
        today = timezone.now().date()
        s1 = baker.make(ReproductiveSeason, name="Spring 2024", start_date=today)
        s2 = baker.make(
            ReproductiveSeason,
            name="Fall 2023",
            start_date=today - timezone.timedelta(days=180),
        )

        url = reverse("reproduction:season_list")

        # Basic List
        response = client.get(url)
        assert response.status_code == 200
        assert s1 in response.context["seasons"]
        assert s2 in response.context["seasons"]

        # Search
        response = client.get(url, {"q": "Spring"})
        assert s1 in response.context["seasons"]
        assert s2 not in response.context["seasons"]

        # Date Filter (start_date__gte)
        response = client.get(url, {"start_date": today.isoformat()})
        assert s1 in response.context["seasons"]
        assert s2 not in response.context["seasons"]

    def test_create_view(self, client, user):
        """Test creating a season."""
        client.force_login(user)
        data = {
            "name": "Winter 2024",
            "start_date": "2024-12-01",
            "end_date": "2025-02-28",
        }
        url = reverse("reproduction:season_add")
        response = client.post(url, data)

        assert response.status_code == 302
        assert ReproductiveSeason.objects.filter(name="Winter 2024").exists()

    def test_update_view(self, client, user):
        """Test updating a season."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason, name="Old Name")
        data = {
            "name": "New Name",
            "start_date": season.start_date,
            "end_date": season.end_date or "",
        }
        url = reverse("reproduction:season_edit", kwargs={"pk": season.pk})
        response = client.post(url, data)

        assert response.status_code == 302
        season.refresh_from_db()
        assert season.name == "New Name"

    def test_delete_view_soft(self, client, user):
        """Test soft delete."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)

        url = reverse("reproduction:season_delete", kwargs={"pk": season.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert not ReproductiveSeason.objects.filter(pk=season.pk).exists()
        assert ReproductiveSeason.all_objects.filter(
            pk=season.pk, is_deleted=True
        ).exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("deleted" in str(m).lower() for m in messages)

    def test_trash_list(self, client, user):
        """Test trash list view."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)
        season.delete()

        url = reverse("reproduction:season_trash")
        response = client.get(url)

        assert response.status_code == 200
        assert season in response.context["seasons"]

    def test_restore_view(self, client, user):
        """Test restore."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)
        season.delete()

        url = reverse("reproduction:season_restore", kwargs={"pk": season.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert ReproductiveSeason.objects.filter(pk=season.pk).exists()

        messages = list(get_messages(response.wsgi_request))
        assert any("restored" in str(m).lower() for m in messages)

    def test_hard_delete_view(self, client, user):
        """Test hard delete."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)
        season.delete()

        url = reverse("reproduction:season_permanent_delete", kwargs={"pk": season.pk})
        response = client.post(url)

        assert response.status_code == 302
        assert not ReproductiveSeason.all_objects.filter(pk=season.pk).exists()

    def test_delete_protected_error(self, client, user):
        """Test delete view handles ProtectedError."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)

        url = reverse("reproduction:season_delete", kwargs={"pk": season.pk})

        with patch(
            "apps.reproduction.models.ReproductiveSeason.delete",
            side_effect=ProtectedError("Protected", []),
        ):
            response = client.post(url)

        assert response.status_code == 200  # Renders template
        assert "Cannot delete" in response.content.decode()

    def test_create_update_context(self, client, user):
        """Test context data for create and update views."""
        client.force_login(user)

        # Create
        url_create = reverse("reproduction:season_add")
        response = client.get(url_create)
        assert response.status_code == 200
        assert "Add Reproductive Season" in response.context["title"]

        # Update
        season = baker.make(ReproductiveSeason)
        url_update = reverse("reproduction:season_edit", kwargs={"pk": season.pk})
        response = client.get(url_update)
        assert response.status_code == 200
        assert "Edit Reproductive Season" in response.context["title"]

    def test_delete_view_get(self, client, user):
        """Test GET request to delete view (confirmation page)."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)
        url = reverse("reproduction:season_delete", kwargs={"pk": season.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "reproduction/season_confirm_delete.html" in [
            t.name for t in response.templates
        ]

    def test_restore_view_get(self, client, user):
        """Test GET request to restore view (confirmation page)."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)
        season.delete()
        url = reverse("reproduction:season_restore", kwargs={"pk": season.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "reproduction/season_confirm_restore.html" in [
            t.name for t in response.templates
        ]

    def test_hard_delete_view_get(self, client, user):
        """Test GET request to hard delete view (confirmation page)."""
        client.force_login(user)
        season = baker.make(ReproductiveSeason)
        season.delete()
        url = reverse("reproduction:season_permanent_delete", kwargs={"pk": season.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "reproduction/season_confirm_permanent_delete.html" in [
            t.name for t in response.templates
        ]
