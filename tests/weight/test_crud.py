# pylint: disable=unused-argument, redefined-outer-name
import pytest
from django.urls import reverse

from apps.cattle.models import Cattle
from apps.weight.models import WeighingSession, WeightRecord


@pytest.mark.django_db
def test_session_crud_operations(client, user_login, weighing_session_factory):
    """Test full lifecycle of a session: Update, Soft Delete, Restore, Hard Delete."""
    session = weighing_session_factory(name="Original Name")

    # 1. Update Session
    update_url = reverse("weight:session-update", args=[session.pk])
    response = client.post(
        update_url,
        {
            "name": "Updated Name",
            "date": session.date,
            "session_type": session.session_type,
        },
    )
    assert response.status_code == 302
    session.refresh_from_db()
    assert session.name == "Updated Name"

    # 2. Soft Delete
    delete_url = reverse("weight:session-delete", args=[session.pk])
    client.post(delete_url)
    assert not WeighingSession.objects.filter(pk=session.pk).exists()
    assert WeighingSession.all_objects.filter(pk=session.pk, is_deleted=True).exists()

    # 3. Restore
    restore_url = reverse("weight:session-restore", args=[session.pk])
    client.post(restore_url)
    assert WeighingSession.objects.filter(pk=session.pk).exists()

    # 4. Hard Delete
    # First soft delete again
    client.post(delete_url)
    hard_delete_url = reverse("weight:session-hard-delete", args=[session.pk])
    client.post(hard_delete_url)
    assert not WeighingSession.all_objects.filter(pk=session.pk).exists()


@pytest.mark.django_db
def test_hard_delete_with_records(client, user_login, weight_record_factory):
    """Test hard deletion of a session including its records (cascade)."""
    record = weight_record_factory()
    session = record.session
    session.soft_delete()

    hard_delete_url = reverse("weight:session-hard-delete", args=[session.pk])
    response = client.post(hard_delete_url)

    assert response.status_code == 302
    assert not WeighingSession.all_objects.filter(pk=session.pk).exists()
    assert not WeightRecord.all_objects.filter(pk=record.pk).exists()


@pytest.mark.django_db
def test_record_crud_operations(client, user_login, weight_record_factory):
    """Test updating and deleting a weight record."""
    record = weight_record_factory(weight_kg=400)
    # create second record so we can delete the first one

    other_cow = Cattle.objects.create(tag="OTHER", weight_kg=100)
    weight_record_factory(session=record.session, animal=other_cow)

    # 1. Update Record
    update_url = reverse("weight:record-update", args=[record.pk])
    response = client.post(
        update_url,
        {"weight_kg": 450, "animal": record.animal.pk, "session": record.session.pk},
    )
    assert response.status_code == 302
    record.refresh_from_db()
    assert record.weight_kg == 450.00

    # 2. Delete Record
    delete_url = reverse("weight:record-delete", args=[record.pk])
    response = client.post(delete_url)
    assert response.status_code == 302
    assert not WeightRecord.objects.filter(pk=record.pk).exists()


@pytest.mark.django_db
def test_session_list_filters(client, user_login, weighing_session_factory):
    """Test filtering mechanism on session list."""
    s1 = weighing_session_factory(name="Spring Weighing", session_type="ROUTINE")
    s2 = weighing_session_factory(name="Sale Weighing", session_type="SALE")

    # Search by name
    url = reverse("weight:session-list")
    response = client.get(url, {"q": "Spring"})
    assert s1 in response.context["sessions"]
    assert s2 not in response.context["sessions"]

    # Filter by type
    response = client.get(url, {"type": "SALE"})
    assert s1 not in response.context["sessions"]
    assert s2 in response.context["sessions"]
