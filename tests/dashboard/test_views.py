import pytest
from django.urls import reverse

from apps.cattle.models import Cattle


@pytest.mark.django_db
def test_dashboard_home_view_context(client):
    """Verify home view loads and context contains aggregated stats."""
    from apps.authentication.models import User

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
    assert "cattle_stats" in response.context
    assert "sales_stats" in response.context
    assert "purchases_stats" in response.context
    assert "net_profit" in response.context

    # Verify logic passed down to template
    stats = response.context["cattle_stats"]
    assert "breed_breakdown" in stats
    assert stats["breed_breakdown"]["Angus"] == 1
    assert stats["total"] == 1
