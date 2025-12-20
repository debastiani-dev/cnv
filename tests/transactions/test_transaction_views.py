import pytest
from django.urls import reverse
from model_bakery import baker

from apps.transactions.models import Transaction


@pytest.mark.django_db
class TestTransactionViews:
    def test_list_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        baker.make(Transaction, _quantity=3)

        url = reverse("transactions:list")
        resp = client.get(url)

        assert resp.status_code == 200
        assert len(resp.context["transactions"]) == 3

    def test_create_view_get(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse("transactions:create")
        resp = client.get(url)

        assert resp.status_code == 200
        assert "items" in resp.context  # Formset

    # Complex POST tests often belong in Integration, but check if we can simple mock one here
    # Merging logic from test_views.py...

    def test_update_view_get(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        transaction = baker.make(Transaction)
        url = reverse("transactions:update", kwargs={"pk": transaction.pk})
        resp = client.get(url)

        assert resp.status_code == 200

    def test_delete_view_post(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        transaction = baker.make(Transaction)
        url = reverse("transactions:delete", kwargs={"pk": transaction.pk})

        resp = client.post(url)

        assert resp.status_code == 302  # Redirect
        transaction.refresh_from_db()
        assert transaction.is_deleted
