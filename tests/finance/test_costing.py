import locale
from decimal import Decimal

import pytest
from django.utils import timezone
from model_bakery import baker

from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.finance.models.finance import CostEntry
from apps.finance.services.costing import CostingService


@pytest.mark.django_db
class TestCosting:
    def setup_method(self):
        try:
            locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
        except locale.Error:
            pass

    def test_money_rounding_brl(self):
        """Verify Round Half Up for BRL"""
        # 2.555 -> 2.56
        val = Decimal("2.555")
        money = Money(val)
        assert money == Decimal("2.56")
        assert str(money) == "2,56"

        # 2.554 -> 2.55
        val2 = Decimal("2.554")
        money2 = Money(val2)
        assert money2 == Decimal("2.55")

    def test_timezone_integrity(self):
        """Verify CostEntry date matches input date regardless of timezone"""
        # Create a cattle first
        cattle = Cattle.objects.create(tag="TEST001", sex="female")

        # Use a specific date
        test_date = timezone.now().date()

        # Create cost entry
        entry = CostingService.create_cost(
            {
                "animal": cattle,
                "date": test_date,
                "category": CostEntry.CATEGORY_NUTRITION,
                "description": "Test Cost",
                "amount": Decimal("100.00"),
            }
        )

        # Reload from DB
        entry.refresh_from_db()
        assert entry.date == test_date

    def test_trash_bin_functionality(self):
        """Verify Soft Delete, Restore, and Hard Delete"""
        cattle = Cattle.objects.create(tag="TEST002", sex="female")
        entry = CostingService.create_cost(
            {
                "animal": cattle,
                "date": timezone.now().date(),
                "category": "HEALTH",
                "description": "Delete Me",
                "amount": Decimal("50.00"),
            }
        )

        # Soft Delete
        CostingService.delete_cost(entry)
        entry.refresh_from_db()
        assert entry.is_deleted is True
        assert (
            entry not in CostEntry.objects.all()
        )  # Should be hidden from default manager
        assert entry in CostEntry.all_objects.all()  # Should be visible in all_objects

        # Restore
        CostingService.restore_cost(entry.pk)
        entry.refresh_from_db()
        assert entry.is_deleted is False
        assert entry in CostEntry.objects.all()

        # Hard Delete
        # First soft delete again (logic might require it, or hard delete works directly? Let's assume hard delete works on deleted items)
        CostingService.delete_cost(entry)
        CostingService.hard_delete_cost(entry.pk)

        assert not CostEntry.all_objects.filter(pk=entry.pk).exists()

    def test_total_cost_calculation(self):
        """Verify Cattle.total_cost property"""
        cattle = Cattle.objects.create(tag="TEST003", sex="female")

        CostingService.create_cost(
            {
                "animal": cattle,
                "date": timezone.now().date(),
                "category": "NUTRITION",
                "description": "Cost 1",
                "amount": Decimal("10.50"),
            }
        )

        CostingService.create_cost(
            {
                "animal": cattle,
                "date": timezone.now().date(),
                "category": "HEALTH",
                "description": "Cost 2",
                "amount": Decimal("20.25"),
            }
        )

        # Total should be 30.75
        # Total should be 30.75
        assert cattle.total_cost == Decimal("30.75")
        assert isinstance(cattle.total_cost, Money)

    def test_create_batch_costs(self):
        """Test creating costs for multiple animals at once."""
        cattle1 = baker.make("cattle.Cattle")
        cattle2 = baker.make("cattle.Cattle")
        cattle_list = [cattle1, cattle2]
        data = {
            "date": timezone.now().date(),
            "category": "NUTRITION",
            "amount": Decimal("100.50"),
            "description": "Bulk feed",
        }

        costs = CostingService.create_batch_costs(cattle_list, data)

        assert len(costs) == 2
        assert CostEntry.objects.count() == 2

        for cost in costs:
            assert cost.category == "NUTRITION"
            assert cost.amount == Decimal("100.50")
            assert cost.description == "Bulk feed"
            assert cost.animal in cattle_list
