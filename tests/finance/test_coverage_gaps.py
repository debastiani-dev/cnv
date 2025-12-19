import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.urls import reverse, reverse_lazy

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.finance.models.finance import CostEntry
from apps.finance.services.costing import CostingService
from apps.finance.templatetags.currency_tags import to_money
from apps.finance.views.cost_views import (
    CostEntryCreateView,
    CostEntryDeleteView,
    CostEntryListView,
    CostEntryTrashListView,
    CostEntryUpdateView,
)


@pytest.mark.django_db
class TestFinanceModels:
    def test_cost_entry_str_and_properties(self):
        cattle = Cattle.objects.create(tag="COV001", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle,
            date="2023-01-01",
            category=CostEntry.CATEGORY_NUTRITION,
            description="Test Desc",
            amount=Decimal("100.50"),
        )
        # Test __str__
        assert str(entry.date) in str(entry)
        assert "Nutrition" in str(entry)
        assert "100,50" in str(entry)  # Assuming BRL locale set in conftest/setup

        # Test money_value property
        assert isinstance(entry.money_value, Money)
        assert entry.money_value == Decimal("100.50")


@pytest.mark.django_db
class TestFinanceService:
    def test_costing_service_update(self):
        cattle = Cattle.objects.create(tag="COV002", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle,
            date="2023-01-01",
            category=CostEntry.CATEGORY_NUTRITION,
            description="Original",
            amount=Decimal("10.00"),
        )

        updated = CostingService.update_cost(
            entry, {"description": "Updated", "amount": Decimal("20.00")}
        )
        assert updated.description == "Updated"
        assert updated.amount == Decimal("20.00")

        entry.refresh_from_db()
        assert entry.description == "Updated"

    def test_costing_service_getters(self):
        # Ensure get_all_costs and get_deleted_costs are hit
        # (Assuming we have some entries from previous tests or empty)
        assert CostingService.get_all_costs() is not None
        assert CostingService.get_deleted_costs() is not None

    def test_allocate_feeding_cost_batch(self):
        mock_animal_1 = Cattle.objects.create(tag="F1", sex="female")
        mock_animal_2 = Cattle.objects.create(tag="F2", sex="female")

        class MockList(list):
            def count(self):
                return len(self)

        animals_list = MockList([mock_animal_1, mock_animal_2])

        mock_event = SimpleNamespace(
            ingredient=SimpleNamespace(
                weighted_average_cost=Decimal("2.00"), name="Corn"
            ),
            amount_kg=Decimal("100.00"),
            date="2023-01-01",
            is_batch=True,
            animals=SimpleNamespace(all=lambda: animals_list),
        )

        # Patch CostEntry class itself to avoid DB model instantiation issues (GenericForeignKey)
        # And patch objects.bulk_create
        with patch("apps.finance.services.costing.CostEntry") as mock_cost_entry_class:
            # We also need to mock objects.bulk_create which is on the class
            mock_manager = MagicMock()
            mock_cost_entry_class.objects = mock_manager

            CostingService.allocate_feeding_cost(mock_event)

            # Verify CostEntry was instantiated twice
            assert mock_cost_entry_class.call_count == 2

            # Verify bulk_create called
            assert mock_manager.bulk_create.called
            entries = mock_manager.bulk_create.call_args[0][0]
            assert len(entries) == 2

            # Verify arguments passed to constructor
            # call_args_list[0] -> first animal
            _, kwargs1 = mock_cost_entry_class.call_args_list[0]
            assert kwargs1["amount"] == Decimal("100.00")
            assert "Corn" in kwargs1["description"]

    def test_allocate_feeding_cost_non_batch(self):
        # Needs structure because fields are accessed before is_batch check (maybe)
        # Actually checking code:
        # ingredient_cost = event.ingredient.weighted_average_cost
        # total_cost = ingredient_cost * event.amount_kg
        # THEN if is_batch...

        mock_event = SimpleNamespace(
            ingredient=SimpleNamespace(
                weighted_average_cost=Decimal("2.00"), name="Corn"
            ),
            amount_kg=Decimal("100.00"),
            date="2023-01-01",
            is_batch=False,
        )
        # Should just pass without error
        CostingService.allocate_feeding_cost(mock_event)


@pytest.mark.django_db
class TestFinanceTemplateTags:
    def test_to_money_none(self):
        assert to_money(None) == "0,00"
        assert (
            to_money(Decimal("10.50")) == "10,50"
            or to_money(Decimal("10.50")) == "10.50"
        )


@pytest.mark.django_db
class TestFinanceViews:
    def test_list_view_queryset(self):
        # Verify get_queryset calls service
        # Minimal mock no longer needed as we call get_queryset on instance directly
        with patch(
            "apps.finance.services.costing.CostingService.get_all_costs"
        ) as mock_get:
            CostEntryListView().get_queryset()
            assert mock_get.called

    def test_create_view_initial(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user", password="pwd")
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW001", sex="female")

        url = reverse("finance:cost-create")
        resp = client.get(url, {"animal": cattle.pk})
        assert resp.status_code == 200
        assert resp.context["form"].initial["animal"] == cattle

    def test_create_view_initial_invalid_animal(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="user_invalid", password="pwd"
        )
        client.force_login(user)

        url = reverse("finance:cost-create")
        # Pass non-existent UUID
        resp = client.get(url, {"animal": uuid.uuid4()})
        assert resp.status_code == 200
        assert "animal" not in resp.context["form"].initial

    def test_create_view_success_redirect_with_animal(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user2", password="pwd")
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW002", sex="female")

        url = reverse("finance:cost-create")
        data = {
            "animal": cattle.pk,
            "date": "2023-01-01",
            "category": CostEntry.CATEGORY_HEALTH,
            "description": "View Test",
            "amount": "50.00",
        }
        resp = client.post(url, data)
        assert resp.status_code == 302
        # Should redirect to cattle detail tab
        expected_url = (
            reverse("cattle:detail", kwargs={"pk": cattle.pk}) + "?tab=financial"
        )
        assert resp.url == expected_url

    def test_create_view_success_url_no_animal(self):
        # Directly test method with mock object
        view = CostEntryCreateView()
        view.object = MagicMock()
        view.object.animal = None
        url = view.get_success_url()
        assert str(url) == reverse_lazy("finance:cost-list")

    def test_update_view_success(self, client, django_user_model):
        user = django_user_model.objects.create_user(
            username="user_upd", password="pwd"
        )
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW_UPD", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle, date="2023-01-01", category="HEALTH", amount=10
        )

        url = reverse("finance:cost-update", kwargs={"pk": entry.pk})
        data = {
            "animal": cattle.pk,
            "date": "2023-01-02",
            "category": CostEntry.CATEGORY_NUTRITION,
            "description": "Updated Test",
            "amount": "60.00",
        }
        resp = client.post(url, data)
        assert resp.status_code == 302
        entry.refresh_from_db()
        assert entry.description == "Updated Test"
        assert entry.amount == Decimal("60.00")

    def test_update_view_success_url_no_animal(self):
        view = CostEntryUpdateView()
        view.object = MagicMock()
        view.object.animal = None
        url = view.get_success_url()
        assert str(url) == reverse_lazy("finance:cost-list")

    def test_delete_view_success_url_no_animal(self):
        view = CostEntryDeleteView()
        view.object = MagicMock()
        view.object.animal = None
        url = view.get_success_url()
        assert str(url) == reverse_lazy("finance:cost-list")

    def test_delete_view_delete_method(self, client, django_user_model):
        """Test sending a DELETE HTTP request to the delete view."""
        user = django_user_model.objects.create_user(
            username="user_del_method", password="pwd"
        )
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW_DEL_M", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle, date="2023-01-01", category="HEALTH", amount=10
        )

        url = reverse("finance:cost-delete", kwargs={"pk": entry.pk})
        resp = client.delete(url)
        assert resp.status_code == 302
        entry.refresh_from_db()
        assert entry.is_deleted

    def test_trash_list_view_queryset(self):
        # Verify get_queryset calls service
        with patch(
            "apps.finance.services.costing.CostingService.get_deleted_costs"
        ) as mock_get:
            CostEntryTrashListView().get_queryset()
            assert mock_get.called

    def test_delete_view_protected_error(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user3", password="pwd")
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW003", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle, date="2023-01-01", category="HEALTH", amount=10
        )

        url = reverse("finance:cost-delete", kwargs={"pk": entry.pk})

        # Mock delete_cost to raise ProtectedError
        with patch(
            "apps.finance.services.costing.CostingService.delete_cost"
        ) as mock_del:
            # ProtectedError requires args: msg, protected_objects
            mock_del.side_effect = ProtectedError("Protected", [])

            resp = client.post(url)
            assert resp.status_code == 200  # Should render the template with error
            # Verify message in content
            content = resp.content.decode()
            # Check English or Portuguese (Case sensitive match found in Mixin: "Cannot")
            assert (
                "Cannot delete" in content
                or "Protected" in content
                or "Não é possível excluir" in content
            )

    def test_delete_view_success_redirect(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user4", password="pwd")
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW004", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle, date="2023-01-01", category="HEALTH", amount=10
        )

        url = reverse("finance:cost-delete", kwargs={"pk": entry.pk})
        resp = client.post(url)
        assert resp.status_code == 302
        expected_url = (
            reverse("cattle:detail", kwargs={"pk": cattle.pk}) + "?tab=financial"
        )
        assert resp.url == expected_url

    def test_restore_view(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user5", password="pwd")
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW005", sex="female")
        # Create deleted entry
        entry = CostEntry.objects.create(
            animal=cattle,
            date="2023-01-01",
            category="HEALTH",
            amount=10,
            is_deleted=True,
        )

        url = reverse("finance:cost-restore", kwargs={"pk": entry.pk})
        resp = client.post(url)
        assert resp.status_code == 302
        entry.refresh_from_db()
        assert not entry.is_deleted

    def test_restore_view_error(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user6", password="pwd")
        client.force_login(user)
        # Invalid PK (random UUID)
        url = reverse("finance:cost-restore", kwargs={"pk": uuid.uuid4()})
        resp = client.post(url)
        assert resp.status_code == 302
        messages = list(get_messages(resp.wsgi_request))
        assert messages  # Should have error message (Object not found)

    def test_permanent_delete_view(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user7", password="pwd")
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW007", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle,
            date="2023-01-01",
            category="HEALTH",
            amount=10,
            is_deleted=True,
        )

        url = reverse("finance:cost-permanent-delete", kwargs={"pk": entry.pk})
        resp = client.post(url)
        assert resp.status_code == 302
        assert not CostEntry.all_objects.filter(pk=entry.pk).exists()

    def test_permanent_delete_view_error(self, client, django_user_model):
        user = django_user_model.objects.create_user(username="user8", password="pwd")
        client.force_login(user)
        url = reverse("finance:cost-permanent-delete", kwargs={"pk": uuid.uuid4()})
        resp = client.post(url)
        assert resp.status_code == 302
        messages = list(get_messages(resp.wsgi_request))
        assert messages

    def test_restore_view_validation_error(self, client, django_user_model):

        user = django_user_model.objects.create_user(
            username="user_restore_err", password="pwd"
        )
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW_REST_ERR", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle,
            date="2023-01-01",
            category="HEALTH",
            amount=10,
            is_deleted=True,
        )
        url = reverse("finance:cost-restore", kwargs={"pk": entry.pk})

        with patch(
            "apps.finance.services.costing.CostingService.restore_cost"
        ) as mock_restore:
            mock_restore.side_effect = ValidationError("Validation Error")
            resp = client.post(url)
            assert resp.status_code == 302
            messages = list(get_messages(resp.wsgi_request))
            assert any("Validation Error" in str(m) for m in messages)

    def test_permanent_delete_view_validation_error(self, client, django_user_model):

        user = django_user_model.objects.create_user(
            username="user_perm_del_err", password="pwd"
        )
        client.force_login(user)
        cattle = Cattle.objects.create(tag="VIEW_PERM_ERR", sex="female")
        entry = CostEntry.objects.create(
            animal=cattle,
            date="2023-01-01",
            category="HEALTH",
            amount=10,
            is_deleted=True,
        )
        url = reverse("finance:cost-permanent-delete", kwargs={"pk": entry.pk})

        with patch(
            "apps.finance.services.costing.CostingService.hard_delete_cost"
        ) as mock_del:
            mock_del.side_effect = ValidationError("Validation Error")
            resp = client.post(url)
            assert resp.status_code == 302
            messages = list(get_messages(resp.wsgi_request))
            assert any("Validation Error" in str(m) for m in messages)
