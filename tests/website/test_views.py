import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_view(client):
    """Test that the home page renders correctly."""
    url = reverse("website:home")  # Assuming namespace is website
    response = client.get(url)
    assert response.status_code == 200
    assert "home" in response.template_name[0]
