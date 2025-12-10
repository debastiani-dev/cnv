import pytest
from django.urls import reverse
from django.utils import timezone

from apps.reproduction.models import ReproductiveSeason


@pytest.mark.django_db
class TestReproductiveSeasonViews:
    def test_list_view_access(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("reproduction:season_list")
        response = client.get(url)
        assert response.status_code == 200
        assert "reproduction/season_list.html" in [t.name for t in response.templates]

    def test_create_view(self, client, admin_user):
        client.force_login(admin_user)
        url = reverse("reproduction:season_add")
        data = {
            "name": "New Season",
            "start_date": timezone.now().date(),
            "active": True,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert ReproductiveSeason.objects.filter(name="New Season").exists()

    def test_update_view(self, client, admin_user):
        client.force_login(admin_user)
        season = ReproductiveSeason.objects.create(
            name="Old Season", start_date=timezone.now().date()
        )
        url = reverse("reproduction:season_edit", kwargs={"pk": season.pk})
        data = {
            "name": "Updated Season",
            "start_date": season.start_date,
        }
        response = client.post(url, data)
        assert response.status_code == 302
        season.refresh_from_db()
        assert season.name == "Updated Season"

    def test_delete_view(self, client, admin_user):
        client.force_login(admin_user)
        season = ReproductiveSeason.objects.create(
            name="Season to Delete", start_date=timezone.now().date()
        )
        url = reverse("reproduction:season_delete", kwargs={"pk": season.pk})
        response = client.post(url)
        assert response.status_code == 302
        assert not ReproductiveSeason.objects.filter(pk=season.pk).exists()

    def test_login_required(self, client):
        url = reverse("reproduction:season_list")
        response = client.get(url)
        assert response.status_code == 302
        assert "login" in response.url
