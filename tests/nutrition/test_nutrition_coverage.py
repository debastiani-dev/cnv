from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery import baker

from apps.locations.models import Location
from apps.nutrition.models import Diet, FeedingEvent


@pytest.mark.django_db
class TestNutritionCoverage:

    def test_diet_create_view_invalid_items(self, client, django_user_model):
        """Test DietCreateView with invalid formset items."""
        user = baker.make(django_user_model)
        client.force_login(user)

        url = reverse("nutrition:diet-create")
        # Submit formset with invalid data: invalid ingredient ID
        # This will cause items.is_valid() to return False in form_valid
        data = {
            "name": "Test Diet",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            # Item 0: has proportion AND an invalid ingredient ID
            "items-0-ingredient": "99999",  # Invalid ingredient ID
            "items-0-proportion_percent": "50.00",
        }

        response = client.post(url, data)

        # Should return 200 with form errors (form_invalid due to invalid formset)
        assert response.status_code == 200

        # Verify diet was NOT created (validation failed before save)
        assert Diet.objects.count() == 0

    def test_diet_update_view_invalid_items(self, client, django_user_model):
        """Test DietUpdateView with invalid formset items."""

        user = baker.make(django_user_model)
        client.force_login(user)

        # Create a diet first
        diet = baker.make(Diet, name="Original Diet")

        url = reverse("nutrition:diet-update", kwargs={"pk": diet.pk})
        # Submit formset with invalid data: invalid ingredient ID
        data = {
            "name": "Updated Diet",
            "items-TOTAL_FORMS": "1",
            "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0",
            "items-MAX_NUM_FORMS": "1000",
            # Item 0: has proportion AND an invalid ingredient ID
            "items-0-ingredient": "99999",  # Invalid ingredient ID
            "items-0-proportion_percent": "50.00",
        }

        response = client.post(url, data)

        # Should return 200 with form errors (form_invalid due to invalid formset)
        assert response.status_code == 200

        # Verify diet name was NOT updated
        diet.refresh_from_db()
        assert diet.name == "Original Diet"

    def test_diet_hard_delete_view_does_not_exist(self, client, django_user_model):
        """Test DietPermanentDeleteView DoesNotExist handling (lines 157-158)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Use invalid UUID
        url = reverse(
            "nutrition:diet-hard-delete",
            kwargs={"pk": "00000000-0000-0000-0000-000000000000"},
        )
        response = client.post(url)

        # Should redirect to trash list even if diet doesn't exist (line 158: pass)
        assert response.status_code == 302
        assert response.url == reverse("nutrition:diet-trash")

    def test_diet_hard_delete_with_error_then_not_exist(
        self, client, django_user_model
    ):
        """Test DietPermanentDeleteView nested DoesNotExist (lines 157-158)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        # Create and soft delete a diet
        diet = baker.make(Diet)
        diet_pk = diet.pk
        diet.delete()  # Soft delete

        url = reverse("nutrition:diet-hard-delete", kwargs={"pk": diet_pk})

        # Mock service to raise ValidationError, then mock get() to raise DoesNotExist
        with patch(
            "apps.nutrition.services.diet_service.DietService.hard_delete_diet",
            side_effect=ValidationError("Error"),
        ):
            with patch(
                "apps.nutrition.models.diet.Diet.all_objects.get",
                side_effect=Diet.DoesNotExist,
            ):
                response = client.post(url)

                # Should redirect to trash despite nested DoesNotExist (line 158: pass)
                assert response.status_code == 302
                assert response.url == reverse("nutrition:diet-trash")

    def test_feeding_event_list_search_filter(self, client, django_user_model):
        """Test FeedingEventListView search filter (line 28)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        location1 = baker.make(Location, name="Pasture A")
        location2 = baker.make(Location, name="Barn B")
        diet1 = baker.make(Diet, name="Summer Mix")
        diet2 = baker.make(Diet, name="Winter Mix")

        event1 = baker.make(FeedingEvent, location=location1, diet=diet1)
        event2 = baker.make(FeedingEvent, location=location2, diet=diet2)

        url = reverse("nutrition:event-list")

        # Test search by location name
        response = client.get(url, {"q": "Pasture"})
        assert response.status_code == 200
        events = list(response.context["events"])
        assert event1 in events
        assert event2 not in events

        # Test search by diet name
        response = client.get(url, {"q": "Winter"})
        assert response.status_code == 200
        events = list(response.context["events"])
        assert event2 in events
        assert event1 not in events

    def test_feeding_event_create_validation_error(self, client, django_user_model):
        """Test FeedingEventCreateView ValidationError handling (lines 62-64)."""
        user = baker.make(django_user_model)
        client.force_login(user)

        location = baker.make(Location)
        diet = baker.make(Diet)

        url = reverse("nutrition:event-create")
        data = {
            "location": location.pk,
            "diet": diet.pk,
            "amount_kg": "100",
            "date": "2024-01-01",
        }

        # Mock FeedingService.record_feeding to raise ValidationError
        with patch(
            "apps.nutrition.services.feeding_service.FeedingService.record_feeding",
            side_effect=ValidationError("Service Error"),
        ):
            response = client.post(url, data)
            assert response.status_code == 200
            # Check that error was added to form
            assert response.context["form"].errors
