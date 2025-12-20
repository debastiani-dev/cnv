# pylint: disable=protected-access
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from model_bakery import baker

from apps.base.management.commands.populate_mock_data import Command
from apps.cattle.models import Cattle
from apps.health.models import SanitaryEvent
from apps.locations.models import Location
from apps.nutrition.models import Diet, FeedingEvent, FeedIngredient
from apps.partners.models import Partner
from apps.reproduction.models import BreedingEvent, Calving
from apps.transactions.models import Transaction


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
            assert len(cattle.tag) <= 25
            assert len(cattle.name) <= 50

        for diet in Diet.objects.all():
            assert len(diet.name) <= 15

        for ingredient in FeedIngredient.objects.all():
            assert len(ingredient.name) <= 15

        for event in SanitaryEvent.objects.all():
            assert len(event.title) <= 15

        for tx in Transaction.objects.all():
            assert len(tx.notes) <= 15

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

    def test_family_generation(self):
        """Test that deep family trees are created."""
        # Run with count=2 (should trigger deep family generation for min(2, 5) = 2 cattle)
        call_command("populate_mock_data", count=2)

        # Check for deep ancestry
        # We expect at least one lineage to go several levels deep
        # Pick the first cow
        cattle = Cattle.objects.all()
        deep_tree_found = False

        for cow in cattle:
            current = cow
            depth = 0
            while current.sire and current.dam:
                depth += 1
                current = current.sire  # Follow sire line
                if depth >= 5:  # We configured depth 8, so 5 should be easy
                    deep_tree_found = True
                    break
            if deep_tree_found:
                break

        assert deep_tree_found, "Did not find any cattle with ancestry depth >= 5"

    def test_user_generation_threshold(self):
        """Test that extra users are created when count is high enough."""
        # Need count/5 > len(existing_users) to trigger creation
        # Existing: 1 superuser + 5 staff = 6.
        # So count/5 > 6 => count > 30. Using 40 ensures loop entry.
        call_command("populate_mock_data", count=40)

        user_model = get_user_model()
        assert user_model.objects.count() > 6

    def test_create_diets_fallback(self):
        """Test that ingredients are created if none exist when creating diets."""
        # Ensure no ingredients exist
        FeedIngredient.objects.all().delete()

        cmd = Command()
        # Mock stdout to silence output
        with patch.object(cmd, "stdout"):
            cmd._create_diets(count=5)

        # Verify ingredients were created
        assert FeedIngredient.objects.count() > 0
        assert Diet.objects.count() >= 5

    @patch("apps.base.management.commands.populate_mock_data.baker.make")
    def test_calf_breed_fallback(self, mock_make):
        """Test that cross-breeding results in 'other' breed (lines 546-551)."""
        cmd = Command()

        # Setup parents with diff breeds
        dam = baker.prepare(Cattle, breed=Cattle.BREED_ANGUS, tag="Dam-001")
        sire = baker.prepare(Cattle, breed=Cattle.BREED_HEREFORD, tag="Sire-001")

        # Pre-prepare breeding event.
        # We assume baker.make is called with BreedingEvent as first arg.
        breeding_event = baker.prepare(BreedingEvent, dam=dam, sire=sire)
        mock_calf = baker.prepare(Cattle, weight_kg=30.0)
        mock_calving = baker.prepare(Calving)

        # side_effect list: 1. BreedingEvent, 2. Calf, 3. Calving
        mock_make.side_effect = [breeding_event, mock_calf, mock_calving]

        # Explicitly pass stdout mock to avoid noise
        with patch.object(cmd, "stdout"):
            cmd._create_calving_records([dam], count=1)

        # Verify the calls to baker.make (BreedingEvent, Calf, Calving)
        assert mock_make.call_count == 3

        # Check args of 2nd call
        _, kwargs = mock_make.call_args_list[1]

        # The logic: if sire.breed != dam.breed -> breed="cross"
        # Since "cross" not in BREED_CHOICES, breed becomes BREED_OTHER ("other")
        assert kwargs.get("breed") == Cattle.BREED_OTHER
