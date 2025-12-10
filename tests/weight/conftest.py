# pylint: disable=unused-argument, redefined-outer-name
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.cattle.models import Cattle
from apps.weight.models import WeighingSession, WeightRecord


@pytest.fixture
def user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(username="testuser", password="password")


@pytest.fixture
def user_login(client, user):
    client.login(username="testuser", password="password")
    return user


@pytest.fixture
def cattle(db):
    return Cattle.objects.create(
        tag="TEST_COW", birth_date=date(2023, 1, 1), weight_kg=Decimal("100.00")
    )


@pytest.fixture
def weighing_session_factory(db):
    def create_session(**kwargs):
        defaults = {
            "date": date(2023, 1, 1),
            "name": "Test Session",
            "session_type": "ROUTINE",
        }
        defaults.update(kwargs)
        return WeighingSession.objects.create(**defaults)

    return create_session


@pytest.fixture
def weight_record_factory(db, cattle, weighing_session_factory):
    def create_record(**kwargs):
        session = kwargs.pop("session", None)
        if not session:
            session = weighing_session_factory()

        animal = kwargs.pop("animal", cattle)

        defaults = {
            "session": session,
            "animal": animal,
            "weight_kg": Decimal("200.00"),
        }
        defaults.update(kwargs)
        return WeightRecord.objects.create(**defaults)

    return create_record
