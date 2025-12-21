# pylint: disable=redefined-outer-name
import uuid
from unittest.mock import patch

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.transactions.forms import TransactionItemForm
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

    def test_update_view_get_with_items(self, client, django_user_model):
        """Test GET with existing items."""
        user = baker.make(django_user_model)
        client.force_login(user)

        tx = baker.make(Transaction)
        baker.make("transactions.TransactionItem", transaction=tx, _quantity=1)

        url = reverse("transactions:update", kwargs={"pk": tx.pk})
        resp = client.get(url)
        assert resp.status_code == 200
        assert "items" in resp.context
        assert len(resp.context["items"]) >= 1

    def test_create_view_post_exception(self, client, django_user_model):
        """Test exception handling during Create POST."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Valid data
        partner = baker.make("partners.Partner")
        form_data = {
            "date": "2023-01-01",
            "type": Transaction.TYPE_SALE,
            "partner": partner.pk,
            "notes": "Test",
            # Formset management form
            "transaction_items-TOTAL_FORMS": "0",
            "transaction_items-INITIAL_FORMS": "0",
            "transaction_items-MIN_NUM_FORMS": "0",
            "transaction_items-MAX_NUM_FORMS": "1000",
        }

        url = reverse("transactions:create")

        # Mock ItemFormSet to be always valid so we reach form.save in form_valid
        with patch(
            "apps.transactions.views.transaction.TransactionItemFormSet"
        ) as mock_itemset:
            mock_items = mock_itemset.return_value
            mock_items.is_valid.return_value = True
            mock_items.save.return_value = None  # Mock save too

            # Mock save to raise exception
            with patch(
                "apps.transactions.forms.TransactionForm.save",
                side_effect=Exception("DB Crash"),
            ):
                resp = client.post(url, form_data)
                assert resp.status_code == 200  # Renders form invalid
                form = resp.context["form"]
                assert "DB Crash" in str(form.non_field_errors())

    def test_transaction_item_form_clean_validation_error(self):
        """Test ValidationError during clean (lines 85-87)."""
        ct = ContentType.objects.get_for_model(Cattle)
        data = {
            "content_type": ct.pk,
            "object_id": uuid.uuid4(),
            "quantity": 1,
            "unit_price": 5000.00,
        }

        # Mock cleaning to raise ValidationError
        # We need to rely on the clean logic calling model.objects.get
        # Since we use UUID, get usually raises DoesNotExist.
        # We patch the model class's objects.get method.

        with patch.object(
            Cattle.objects,
            "get",
            side_effect=ValidationError("Custom Validation Error"),
        ):
            form = TransactionItemForm(data=data)
            assert not form.is_valid()
            assert "object_id" in form.errors
            assert "Custom Validation Error" in str(form.errors["object_id"])

    def test_delete_view_post(self, client, django_user_model):
        user = baker.make(django_user_model)
        client.force_login(user)

        transaction = baker.make(Transaction)
        url = reverse("transactions:delete", kwargs={"pk": transaction.pk})

        resp = client.post(url)

        assert resp.status_code == 302  # Redirect
        transaction.refresh_from_db()
        assert transaction.is_deleted

    def test_create_view_post_success(self, client, django_user_model):
        """Test successful creation with valid items."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make("partners.Partner")

        # We need to construct formset data properly or mock validation/save.
        # Constructing formset data is robust.
        # Management form + 1 item

        form_data = {
            "date": "2023-01-01",
            "type": Transaction.TYPE_SALE,
            "partner": partner.pk,
            "notes": "Success Note",
            "transaction_items-TOTAL_FORMS": "1",
            "transaction_items-INITIAL_FORMS": "0",
            "transaction_items-MIN_NUM_FORMS": "0",
            "transaction_items-MAX_NUM_FORMS": "1000",
            # Item 0
            "transaction_items-0-content_type": "",  # Leave blank? Usually required.
            "transaction_items-0-object_id": "",
            "transaction_items-0-quantity": "",
            "transaction_items-0-unit_price": "",
        }
        # If we send empty item it might be ignored if not required, but extra=1.
        # Let's mock the FormSet to avoid data complexity and focus on View Logic coverage?
        # Mocking is safer for View Logic unit testing.

        url = reverse("transactions:create")

        with patch(
            "apps.transactions.views.transaction.TransactionItemFormSet"
        ) as mock_itemset:
            mock_items = mock_itemset.return_value
            mock_items.is_valid.return_value = True
            mock_items.instance = None  # Will be set by view
            mock_items.save.return_value = []

            resp = client.post(url, form_data)
            assert resp.status_code == 302
            assert Transaction.objects.filter(notes="Success Note").exists()

    def test_create_view_post_invalid_items(self, client, django_user_model):
        """Test creation with invalid items (line 88)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        partner = baker.make("partners.Partner")

        form_data = {
            "date": "2023-01-01",
            "type": Transaction.TYPE_SALE,
            "partner": partner.pk,
            "notes": "Invalid Items",
            # Management form is needed to pass FormSet init usually
            "transaction_items-TOTAL_FORMS": "1",
            "transaction_items-INITIAL_FORMS": "0",
            "transaction_items-MIN_NUM_FORMS": "0",
            "transaction_items-MAX_NUM_FORMS": "1000",
        }

        url = reverse("transactions:create")

        with patch(
            "apps.transactions.views.transaction.TransactionItemFormSet"
        ) as mock_itemset:
            mock_items = mock_itemset.return_value
            mock_items.is_valid.return_value = False  # Invalid

            resp = client.post(url, form_data)
            assert resp.status_code == 200  # Re-renders
            assert "items" in resp.context
            assert not Transaction.objects.filter(notes="Invalid Items").exists()

    def test_update_view_post_success(self, client, django_user_model):
        """Test successful update."""
        user = baker.make(django_user_model)
        client.force_login(user)
        tx = baker.make(Transaction, notes="Old Note")

        form_data = {
            "date": tx.date,
            "type": tx.type,
            "partner": tx.partner.pk,
            "notes": "Updated Note",
            "transaction_items-TOTAL_FORMS": "1",
            "transaction_items-INITIAL_FORMS": "0",
            "transaction_items-MIN_NUM_FORMS": "0",
            "transaction_items-MAX_NUM_FORMS": "1000",
        }

        url = reverse("transactions:update", kwargs={"pk": tx.pk})

        with patch(
            "apps.transactions.views.transaction.TransactionItemFormSet"
        ) as mock_itemset:
            mock_items = mock_itemset.return_value
            mock_items.is_valid.return_value = True

            resp = client.post(url, form_data)
            assert resp.status_code == 302
            tx.refresh_from_db()
            assert tx.notes == "Updated Note"

    def test_update_view_post_invalid(self, client, django_user_model):
        """Test invalid update (invalid items)."""
        user = baker.make(django_user_model)
        client.force_login(user)
        tx = baker.make(Transaction, notes="Old Note")

        form_data = {
            "date": tx.date,
            "type": tx.type,
            "partner": tx.partner.pk,
            "notes": "Updated Note",
            "transaction_items-TOTAL_FORMS": "1",
            "transaction_items-INITIAL_FORMS": "0",
            "transaction_items-MIN_NUM_FORMS": "0",
            "transaction_items-MAX_NUM_FORMS": "1000",
        }

        url = reverse("transactions:update", kwargs={"pk": tx.pk})

        with patch(
            "apps.transactions.views.transaction.TransactionItemFormSet"
        ) as mock_itemset:
            mock_items = mock_itemset.return_value
            mock_items.is_valid.return_value = False

            resp = client.post(url, form_data)
            assert resp.status_code == 200
            assert "items" in resp.context
            tx.refresh_from_db()
            assert tx.notes == "Old Note"
