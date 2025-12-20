import pytest
from django.urls import reverse
from model_bakery import baker

from apps.transactions.models import Transaction


@pytest.mark.django_db
class TestTransactionTrash:
    def test_trash_list_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        # Soft delete some transactions
        tx1 = baker.make(Transaction)
        tx1.delete()

        tx2 = baker.make(Transaction)  # Not deleted

        url = reverse("transactions:trash")
        resp = client.get(url)

        assert resp.status_code == 200
        assert tx1 in resp.context["transactions"]
        assert tx2 not in resp.context["transactions"]

    def test_restore_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        tx = baker.make(Transaction)
        tx.delete()
        assert tx.is_deleted

        url = reverse("transactions:restore", kwargs={"pk": tx.pk})
        resp = client.post(url)

        assert resp.status_code == 302
        tx.refresh_from_db()
        assert not tx.is_deleted

    def test_hard_delete_view(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        tx = baker.make(Transaction)
        tx.delete()

        url = reverse("transactions:permanent-delete", kwargs={"pk": tx.pk})
        resp = client.post(url)

        assert resp.status_code == 302

        # Verify completely gone
        with pytest.raises(Transaction.DoesNotExist):
            Transaction.all_objects.get(pk=tx.pk)
