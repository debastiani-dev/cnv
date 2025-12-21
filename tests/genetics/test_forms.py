# pylint: disable=unused-argument, redefined-outer-name
import pytest

from apps.cattle.models import Cattle
from apps.genetics.forms import StockAdjustmentForm
from apps.genetics.models import SemenBatch, StorageTank


@pytest.fixture
def form_setup(db):
    tank = StorageTank.objects.create(name="Tank 1", capacity_liters=20)
    bull = Cattle.objects.create(tag="BULL01", sex=Cattle.SEX_MALE)
    batch = SemenBatch.objects.create(
        tank=tank,
        bull=bull,
        batch_code="B001",
        initial_quantity=10,
        current_quantity=10,
        purchase_date="2023-01-01",
        cost_per_unit=10,
    )
    return batch


@pytest.mark.django_db
def test_stock_adjustment_form_no_batch():
    """Test calling apply_adjustment without a batch instance."""
    form = StockAdjustmentForm(data={"adjustment_type": "LOSS", "quantity": 1})
    assert form.is_valid()
    # Should not raise error and do nothing
    form.apply_adjustment()


@pytest.mark.django_db
def test_stock_adjustment_form_loss_validation(form_setup):
    """Test validation when removing more than available."""
    batch = form_setup
    form = StockAdjustmentForm(
        data={"adjustment_type": "LOSS", "quantity": 100}, batch=batch
    )
    assert not form.is_valid()
    assert "Cannot remove 100 units" in form.errors["__all__"][0]
