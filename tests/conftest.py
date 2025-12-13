# pylint: disable=unused-argument
import pytest
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
