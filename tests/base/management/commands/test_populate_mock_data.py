from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.base.management.commands.populate_mock_data import Command
from apps.cattle.models import Cattle
from apps.health.models import SanitaryEvent
from apps.locations.models import Location
from apps.nutrition.models import Diet, FeedingEvent, FeedIngredient
from apps.partners.models import Partner
from apps.purchases.models import Purchase
from apps.sales.models import Sale


@pytest.mark.django_db
class TestPopulateMockData:
    """Tests for the populate_mock_data management command."""

    def test_command_execution(self):
        """Test full execution of the command with small count."""
        # Run with count=2 to be fast
        call_command("populate_mock_data", count=2)

        # Verify DB population
        assert Partner.objects.count() >= 2
        assert (
            Location.objects.count() >= 1
        )  # Locations are fixed at 5 usually, or count? Script code: locations count is fixed range(5)
        # Wait, the script says `for _ in range(5): locations.append(...)`. So simple run makes 5.

        assert Cattle.objects.count() >= 2
        assert Diet.objects.count() >= 2
        assert FeedingEvent.objects.count() >= 2

        # Verify String constraints (<= 15 chars)
        for partner in Partner.objects.all():
            assert len(partner.name) <= 15

        for loc in Location.objects.all():
            assert len(loc.name) <= 15

        for cattle in Cattle.objects.all():
            assert len(cattle.tag) <= 15
            assert len(cattle.name) <= 15

        for diet in Diet.objects.all():
            assert len(diet.name) <= 15

        for ingredient in FeedIngredient.objects.all():
            assert len(ingredient.name) <= 15

        for event in SanitaryEvent.objects.all():
            assert len(event.title) <= 15

        for sale in Sale.objects.all():
            assert len(sale.notes) <= 15

        for purchase in Purchase.objects.all():
            assert len(purchase.notes) <= 15

    def test_short_str(self):
        """Test _short_str helper (lines 44-55)."""
        cmd = Command()
        # pylint: disable=protected-access
        s = cmd._short_str("Pre")
        assert len(s) == 15
        assert s.startswith("Pre-")

        # Test short prefix fallback
        # pylint: disable=protected-access
        long_prefix = "A" * 20
        s2 = cmd._short_str(long_prefix)
        assert len(s2) == 15
        assert s2 == "A" * 15

        # Boundary case (prefix length 14, leaves 0 for random? Logic says 15 - len - 1)
        # Logic: if available < 1: return prefix[:15]
        s3 = cmd._short_str("A" * 14)
        assert len(s3) == 14  # Just returns prefix if no space for suffix

        s4 = cmd._short_str("A" * 13)
        # 15 - 13 - 1 = 1 available.
        assert len(s4) <= 15
        assert "-" in s4

    def test_error_handling(self):
        """Test that command handles exceptions properly."""
        with patch.object(
            Command, "_create_partners", side_effect=ValueError("Simulated Failure")
        ):
            with pytest.raises(ValueError, match="Simulated Failure"):
                call_command("populate_mock_data", count=1)
