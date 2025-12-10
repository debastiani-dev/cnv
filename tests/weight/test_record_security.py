# pylint: disable=unused-argument
import pytest
from django.urls import reverse

from apps.cattle.models import Cattle
from apps.weight.models import WeightRecord


@pytest.mark.django_db
def test_prevent_last_record_deletion(client, user_login, weight_record_factory):
    """
    Test that the last record in a session cannot be deleted.
    """
    # Create a record (and implicitly a session with 1 record)
    record1 = weight_record_factory()
    session = record1.session

    # Attempt to delete the only record
    delete_url = reverse("weight:record-delete", args=[record1.pk])
    response = client.post(delete_url)

    # Should redirect back to session detail
    assert response.status_code == 302
    assert response.url == reverse("weight:session-detail", kwargs={"pk": session.pk})

    # Record should still exist
    assert WeightRecord.objects.filter(pk=record1.pk).exists()

    # Check for error message (requires inspecting messages, difficult with simple client,
    # but existence of object proves validation worked)

    # Now add a second record with a DIFFERENT animal
    new_cow = Cattle.objects.create(tag="COW2", weight_kg=100)
    record2 = weight_record_factory(session=session, animal=new_cow)
    assert session.records.count() == 2

    # Attempt to delete the first record again
    response = client.post(delete_url)

    # Should succeed now
    assert response.status_code == 302
    assert not WeightRecord.objects.filter(pk=record1.pk).exists()

    # Second record should still be there
    assert WeightRecord.objects.filter(pk=record2.pk).exists()

    # Now try to delete the last remaining one (record2)
    delete_url_2 = reverse("weight:record-delete", args=[record2.pk])
    client.post(delete_url_2)

    # Should be blocked again
    assert WeightRecord.objects.filter(pk=record2.pk).exists()
