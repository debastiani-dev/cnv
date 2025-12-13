# pylint: disable=unused-argument
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(username="testuser", password="testpass123")
