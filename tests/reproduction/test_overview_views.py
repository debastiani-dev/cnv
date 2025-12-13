import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.models import BreedingEvent, Calving, ReproductiveSeason


@pytest.mark.django_db
class TestReproductionOverviewView:
    """Tests for ReproductionOverviewView."""

    def test_overview_stats(self, client, user):
        """Test overview dashboard statistics."""
        client.force_login(user)

        # Setup stats
        # Total females = 4 active
        baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
        )
        baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_BRED,
        )
        baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
        )
        # Inactive one (should not count)
        baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_DEAD,
            reproduction_status=Cattle.REP_STATUS_OPEN,
        )
        # Male (should not count)
        baker.make(Cattle, sex=Cattle.SEX_MALE, status=Cattle.STATUS_AVAILABLE)

        response = client.get(reverse("reproduction:overview"))

        assert response.status_code == 200
        assert response.context["total_females"] == 3
        assert response.context["open_cows"] == 1
        assert response.context["bred_cows"] == 1
        assert response.context["pregnant_cows"] == 1

    def test_recent_activity_context(self, client, user):
        """Test recent activity context data."""
        client.force_login(user)

        # Create 6 breedings to test limit 5
        baker.make(BreedingEvent, _quantity=6)
        # Create 6 calvings
        baker.make(Calving, _quantity=6)

        response = client.get(reverse("reproduction:overview"))

        assert len(response.context["recent_breedings"]) == 5
        assert len(response.context["recent_calvings"]) == 5

    def test_active_season_context(self, client, user):
        """Test active season determination."""
        client.force_login(user)
        today = timezone.now().date()

        # Active season
        active = baker.make(
            ReproductiveSeason,
            start_date=today,
            end_date=today + timezone.timedelta(days=30),
        )
        # Past season
        baker.make(
            ReproductiveSeason,
            start_date=today - timezone.timedelta(days=60),
            end_date=today - timezone.timedelta(days=30),
        )

        response = client.get(reverse("reproduction:overview"))

        assert response.context["active_season"] == active

    def test_no_active_season(self, client, user):
        """Test context when no season is active."""
        client.force_login(user)
        # No seasons

        response = client.get(reverse("reproduction:overview"))

        assert response.context["active_season"] is None
