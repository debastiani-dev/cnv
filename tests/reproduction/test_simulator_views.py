from datetime import timedelta

# pylint: disable=redefined-outer-name
import pytest
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.reproduction.models import MatingPlan, ReproductiveSeason
from apps.reproduction.services.genetics import InbreedingService


@pytest.fixture
def simulator_url():
    return reverse("reproduction:mating_simulator")


@pytest.fixture
def analysis_url():
    return reverse("reproduction:mating_analyze")


@pytest.fixture
def create_plan_url():
    return reverse("reproduction:mating_create_bulk")


@pytest.mark.django_db
class TestMatingSimulatorView:
    def test_get_context_data(self, client, user, simulator_url):
        """Test that the simulator page loads with correct context data."""
        client.force_login(user)

        # Setup data
        sire = baker.make(
            Cattle, sex=Cattle.SEX_MALE, status=Cattle.STATUS_AVAILABLE, tag="Bull-001"
        )
        cow_open = baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            tag="Cow-001",
        )
        cow_lactating = baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_LACTATING,
            tag="Cow-002",
        )
        cow_pregnant = baker.make(
            Cattle,
            sex=Cattle.SEX_FEMALE,
            status=Cattle.STATUS_AVAILABLE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            tag="Cow-003",
        )  # Should be excluded

        response = client.get(simulator_url)

        assert response.status_code == 200
        assert "sires" in response.context
        assert "cows" in response.context

        sires = response.context["sires"]
        cows = response.context["cows"]

        assert sire in sires
        assert cow_open in cows
        assert cow_lactating in cows
        assert cow_pregnant not in cows


@pytest.mark.django_db
class TestMatingAnalysisView:
    def test_post_success(self, client, user, analysis_url):
        """Test successful analysis calculation."""
        client.force_login(user)

        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)

        payload = {"sire_id": sire.pk, "cow_ids": [cow.pk]}

        response = client.post(
            analysis_url, data=payload, content_type="application/json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["cow_id"] == str(cow.pk)
        assert data["results"][0]["risk_level"] == InbreedingService.RISK_SAFE

    def test_post_missing_data(self, client, user, analysis_url):
        """Test bad request when data is missing."""
        client.force_login(user)

        response = client.post(analysis_url, data={}, content_type="application/json")
        assert response.status_code == 400

        # Missing sire
        response = client.post(
            analysis_url, data={"cow_ids": [1]}, content_type="application/json"
        )
        assert response.status_code == 400

    def test_post_sire_not_found(self, client, user, analysis_url):
        """Test 404 when sire does not exist."""
        client.force_login(user)

        response = client.post(
            analysis_url,
            data={"sire_id": 99999, "cow_ids": [1]},
            content_type="application/json",
        )
        assert response.status_code == 404


@pytest.mark.django_db
class TestMatingPlanBulkCreateView:
    def test_post_success(self, client, user, create_plan_url):
        """Test successful plan creation."""
        client.force_login(user)

        # Ensure Active Season
        season = baker.make(
            ReproductiveSeason,
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
        )
        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)

        payload = {"sire_id": sire.pk, "cow_ids": [cow.pk]}

        response = client.post(
            create_plan_url, data=payload, content_type="application/json"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify DB
        plan = MatingPlan.objects.get(pk=data["plan_id"])
        assert plan.sire == sire
        assert plan.season == season
        assert plan.status == MatingPlan.Status.APPROVED_WAITING
        assert plan.cows.count() == 1
        assert cow in plan.cows.all()

    def test_post_missing_data(self, client, user, create_plan_url):
        client.force_login(user)
        response = client.post(
            create_plan_url, data={}, content_type="application/json"
        )
        assert response.status_code == 400

    def test_post_sire_not_found(self, client, user, create_plan_url):
        client.force_login(user)
        response = client.post(
            create_plan_url,
            data={"sire_id": 99999, "cow_ids": [1]},
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_post_no_season(self, client, user, create_plan_url):
        """Test error when no reproductive season is active."""
        client.force_login(user)
        ReproductiveSeason.objects.all().delete()

        sire = baker.make(Cattle, sex=Cattle.SEX_MALE)
        cow = baker.make(Cattle, sex=Cattle.SEX_FEMALE)

        payload = {"sire_id": sire.pk, "cow_ids": [cow.pk]}

        response = client.post(
            create_plan_url, data=payload, content_type="application/json"
        )

        assert response.status_code == 400
        assert "No active Reproductive Season" in response.json()["error"]
