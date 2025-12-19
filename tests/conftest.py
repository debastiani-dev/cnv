# pylint: disable=unused-argument
import locale

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from model_bakery import baker

from apps.cattle.models.cattle import Cattle

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
    return baker.make(Cattle, sex=Cattle.SEX_MALE)


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
