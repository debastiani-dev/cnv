import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.reproduction.models import ReproductiveSeason


@pytest.mark.django_db
class TestSeasonCoverage:

    def test_season_list_end_date_filter(self, client, django_user_model):
        """Test season list view start_date__lte filter (line 40)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        s1 = baker.make(
            ReproductiveSeason, start_date=timezone.now().date(), name="Season 1"
        )
        # Season far in future
        future_date = timezone.now().date() + timezone.timedelta(days=365)
        s2 = baker.make(ReproductiveSeason, start_date=future_date, name="Season 2")

        url = reverse("reproduction:season_list")

        # Filter end_date should show seasons starting ON or BEFORE that date
        limit_date = timezone.now().date() + timezone.timedelta(days=10)

        response = client.get(url, {"end_date": str(limit_date)})
        assert s1 in response.context["seasons"]
        assert s2 not in response.context["seasons"]
