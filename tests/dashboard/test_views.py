import pytest
from django.urls import reverse

from apps.authentication.models import User
from apps.cattle.models import Cattle


@pytest.mark.django_db
def test_dashboard_home_view_context(client):
    """Verify home view loads and context contains aggregated stats."""

    # Setup User and Login
    user = User.objects.create_user(username="testuser", password="password")
    client.force_login(user)

    # Setup Data
    Cattle.objects.create(
        breed=Cattle.BREED_ANGUS, status=Cattle.STATUS_AVAILABLE, weight_kg=100
    )

    url = reverse("dashboard:home")
    response = client.get(url)

    assert response.status_code == 200

    # Check context data presence
    # Check context data presence
    assert "alerts" in response.context
    assert "finance" in response.context
    assert "commercial" in response.context
    assert "herd" in response.context
    assert "operations" in response.context

    # Verify logic passed down to template
    herd = response.context["herd"]
    assert "total_headcount" in herd
    assert herd["total_headcount"] == 1


@pytest.mark.django_db
def test_stocking_rate_api_view(client):
    """Test StockingRateApiView returns JSON data."""
    user = User.objects.create_user(username="testuser", password="password")
    client.force_login(user)

    url = reverse("dashboard:stocking-rate-api")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = response.json()
    assert "rate" in data
    assert "total_au" in data
    assert "total_area" in data


@pytest.mark.django_db
def test_adg_trend_api_view(client):
    """Test AdgTrendApiView returns JSON data."""
    user = User.objects.create_user(username="testuser", password="password")
    client.force_login(user)

    url = reverse("dashboard:adg-trend-api")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = response.json()
    assert "value" in data
    assert "unit" in data
    assert "trend" in data
    assert "status" in data
    assert "history" in data


@pytest.mark.django_db
def test_financial_trend_api_view(client):
    """Test ChartFinancialTrendApiView returns JSON data."""
    user = User.objects.create_user(username="testuser", password="password")
    client.force_login(user)

    url = reverse("dashboard:chart-financial-trend")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    data = response.json()
    assert "sales" in data
    assert "costs" in data


@pytest.mark.django_db
def test_genetic_progress_api_view(client):
    """Test ChartGeneticProgressApiView returns JSON data."""
    user = User.objects.create_user(username="testuser", password="password")
    client.force_login(user)

    url = reverse("dashboard:chart-genetic-progress")
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.django_db
def test_api_views_require_authentication(client):
    """Test that API views require login."""
    # Test without login
    stocking_url = reverse("dashboard:stocking-rate-api")
    adg_url = reverse("dashboard:adg-trend-api")
    fin_url = reverse("dashboard:chart-financial-trend")
    gen_url = reverse("dashboard:chart-genetic-progress")

    response = client.get(stocking_url)
    assert response.status_code == 302  # Redirect to login

    response = client.get(adg_url)
    assert response.status_code == 302  # Redirect to login

    response = client.get(fin_url)
    assert response.status_code == 302

    response = client.get(gen_url)
    assert response.status_code == 302
