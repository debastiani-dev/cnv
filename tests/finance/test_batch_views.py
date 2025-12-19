import uuid

import pytest
from django.urls import reverse
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.finance.models.finance import CostEntry


@pytest.mark.django_db
class TestCostBatchCreateView:
    def test_cost_batch_create_initial_load(self, client, user):
        """
        Tests the initial POST request (from cattle list "add cost" button)
        which should render the form with selected cattle.
        """
        client.force_login(user)
        cattle1 = baker.make(Cattle)
        cattle2 = baker.make(Cattle)
        url = reverse("finance:cost-batch-create")

        # Simulate selecting cattle from the list and clicking "Add Cost"
        data = {
            "cattle_ids": f"{cattle1.pk},{cattle2.pk}",
            "action": "add_cost",  # Mimic the list action
        }

        response = client.post(url, data)

        assert response.status_code == 200
        assert "finance/cost_batch_add.html" in [t.name for t in response.templates]
        # Verify the form is rendered with cattle_ids
        form = response.context["form"]
        assert form.initial["cattle_ids"] == f"{cattle1.pk},{cattle2.pk}"

    def test_cost_batch_create_submit_success(self, client, user):
        """
        Tests the second POST request (submitting the filled form)
        which should create costs and redirect.
        """
        client.force_login(user)
        cattle1 = baker.make(Cattle)
        cattle2 = baker.make(Cattle)
        category = "NUTRITION"
        url = reverse("finance:cost-batch-create")

        data = {
            "cattle_ids": f"{cattle1.pk},{cattle2.pk}",
            "date": "2023-10-27",
            "category": category,
            "amount": "50.00",
            "description": "Batch feed",
        }

        response = client.post(url, data, follow=True)

        assert response.status_code == 200
        assert CostEntry.objects.count() == 2

        cost1 = CostEntry.objects.get(animal=cattle1)
        assert cost1.category == category
        assert str(cost1.amount) == "50.00"

        cost2 = CostEntry.objects.get(animal=cattle2)
        assert cost2.category == category

        # Check success message
        messages = list(response.context["messages"])
        assert len(messages) == 1
        assert "Successfully added costs for 2 animals." in str(messages[0])

    def test_cost_batch_create_invalid_cattle(self, client, user):
        """
        Tests submission with invalid cattle IDs (e.g. empty or non-existent).
        """
        client.force_login(user)
        url = reverse("finance:cost-batch-create")

        data = {
            "cattle_ids": str(uuid.uuid4()),  # Non-existent but valid format
            "date": "2023-10-27",
            "category": "NUTRITION",
            "amount": "50.00",
            "description": "Test description",  # Required field!
        }

        response = client.post(url, data)  # Should re-render form with error

        assert response.status_code == 200  # Re-renders form
        messages = list(response.context["messages"])

        # Now we can safely assert the specific error message because form_valid was actually called
        assert any(
            "Select at least one animal" in str(m)
            or "Invalid cattle" in str(m)
            or "Seleção de gado" in str(m)
            for m in messages
        )
        assert CostEntry.objects.count() == 0
