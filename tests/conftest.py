# pylint: disable=unused-argument, redefined-outer-name
import locale

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.genetics.models.genetics import SemenBatch, StorageTank
from apps.partners.models.partner import Partner

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def cattle():
    return baker.make(Cattle, sex=Cattle.SEX_FEMALE)


@pytest.fixture
def bull():
    return baker.make(
        Cattle, sex=Cattle.SEX_MALE, tag="BULL01", status=Cattle.STATUS_AVAILABLE
    )


@pytest.fixture
def tank(db):
    return StorageTank.objects.create(name="Tank 1", capacity_liters=20)


@pytest.fixture
def partner(db):
    return Partner.objects.create(name="Supplier 1", is_supplier=True, is_customer=True)


@pytest.fixture
def semen_batch(db, tank, bull):
    return SemenBatch.objects.create(
        tank=tank,
        canister="A1",
        initial_quantity=100,
        current_quantity=100,
        purchase_date="2023-01-01",
        bull=bull,
        batch_code="B001",
        cost_per_unit=50.00,
    )


def pytest_configure(config):
    """
    Override settings for all tests to use standard static files storage.
    This prevents 'Missing staticfiles manifest entry' errors when using WhiteNoise with tests.
    """
    settings.STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

    try:
        locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
    except locale.Error:
        # Fallback if locale is not generated (e.g. in CI without full locales)
        pass
