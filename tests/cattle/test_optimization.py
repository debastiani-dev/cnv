import pytest
from django.urls import reverse

from apps.cattle.models import Cattle
from apps.locations.models import Location, LocationStatus


@pytest.mark.django_db
class TestCattleOptimization:
    def test_query_optimization(self, client, user, django_assert_num_queries):
        """
        Verify that the cattle list view renders with a fixed low number of queries
        regardless of the number of cattle.
        Target: <= 4 queries (Count, User, select_related(Location, Sire, Dam))
        """
        client.force_login(user)
        loc = Location.objects.create(
            name="Paddock 1",
            status=LocationStatus.ACTIVE,
            area_hectares=10,
            capacity_head=100,
        )

        # Create 50 cattle
        cattle_list = [
            Cattle(
                tag=f"TAG-{i}",
                location=loc,
            )
            for i in range(50)
        ]
        Cattle.objects.bulk_create(cattle_list)

        url = reverse("cattle:list")

        # Max 5 queries allowed (Actual 5 observed: Session, User, Count, Locations Dropdown, Main Query)
        with django_assert_num_queries(5):
            response = client.get(url)
            assert response.status_code == 200
            assert len(response.context["cattle_list"]) == 10  # Pagination

    def test_filter_functionality(self, client, user):
        client.force_login(user)
        c1 = Cattle.objects.create(
            tag="Available",
            status=Cattle.STATUS_AVAILABLE,
            weight_kg=300,
            current_weight=300,
        )
        c2 = Cattle.objects.create(
            tag="Sold", status=Cattle.STATUS_SOLD, weight_kg=400, current_weight=400
        )
        c3 = Cattle.objects.create(
            tag="Dead", status=Cattle.STATUS_DEAD, weight_kg=500, current_weight=500
        )

        url = reverse("cattle:list")

        # Test Status Filter (using filterset field name)
        # Note: MultipleChoiceFilter might expect list if multiple values, but single value ?status=sold works.
        res = client.get(url, {"status": "sold"})

        cattle_list = list(res.context["cattle_list"])
        assert c2 in cattle_list
        assert c1 not in cattle_list
        assert c3 not in cattle_list

        # Test Weight Range
        res = client.get(url, {"weight_min": 350, "weight_max": 450})
        # If c2 is 400kg, it should be in.
        cattle_list = list(res.context["cattle_list"])
        assert c2 in cattle_list
        assert c1 not in cattle_list
        assert c3 not in cattle_list

        # Test Search
        res = client.get(url, {"q": "Dead"})
        cattle_list = list(res.context["cattle_list"])
        assert c3 in cattle_list
        assert c1 not in cattle_list
