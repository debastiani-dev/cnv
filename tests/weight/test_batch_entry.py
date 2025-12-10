# pylint: disable=unused-argument
import pytest
from django.urls import reverse

from apps.weight.models import WeighingSession


@pytest.mark.django_db
def test_create_session_redirects_to_batch_entry(client, user_login, cattle):
    """
    Test that creating a session with selected cattle redirects to the batch entry page,
    confirming the URL configuration is correct.
    """
    url = reverse("weight:session-create")

    # cattle fixture is a specific object, assume we have its ID
    cattle_ids = [cattle.pk]

    response = client.post(
        url,
        {
            "date": "2025-01-01",
            "name": "Batch Test Session",
            "session_type": "ROUTINE",
            "cattle_ids": cattle_ids,
        },
    )

    # Should redirect to batch-entry
    assert response.status_code == 302

    session = WeighingSession.objects.get(name="Batch Test Session")
    expected_url = reverse("weight:batch-entry", kwargs={"pk": session.pk})

    # Assert redirect location matches expected URL
    assert response.url == expected_url


@pytest.mark.django_db
def test_access_batch_entry_page(client, user_login, weighing_session_factory):
    """Test accessing the batch entry page directly."""
    session = weighing_session_factory()
    url = reverse("weight:batch-entry", kwargs={"pk": session.pk})

    response = client.get(url)
    assert (
        response.status_code == 302
    )  # Should redirect to detail because no cattle selected in session/query param
    assert response.url == reverse("weight:session-detail", kwargs={"pk": session.pk})
