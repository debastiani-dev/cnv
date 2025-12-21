# pylint: disable=unused-argument, redefined-outer-name
import pytest

from apps.authentication.models.user import User
from apps.base.utils.money import Money
from apps.cattle.models import Cattle
from apps.commercial.models import SalesEvent, SalesLot
from apps.commercial.services.commercial_service import CommercialService
from apps.genetics.models import SemenBatch, StorageTank
from apps.partners.models import Partner


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="password")


@pytest.fixture
def partner(db):
    return Partner.objects.create(name="Buyer", is_customer=True)


@pytest.fixture
def event(db):
    return SalesEvent.objects.create(
        name="Auction", date="2023-01-01", sales_type=SalesEvent.TYPE_AUCTION
    )


@pytest.fixture
def tank(db):
    return StorageTank.objects.create(name="Tank", capacity_liters=10)


@pytest.fixture
def bull(db):
    return Cattle.objects.create(tag="BULL", sex=Cattle.SEX_MALE)


@pytest.fixture
def semen_batch(db, tank, bull):
    return SemenBatch.objects.create(
        tank=tank,
        bull=bull,
        batch_code="B1",
        initial_quantity=100,
        current_quantity=100,
        purchase_date="2023-01-01",
        cost_per_unit=10,
    )


@pytest.mark.django_db
def test_close_lot_reduces_inventory(event, semen_batch, partner):
    """Test that closing a genetic lot reduces the inventory of the batch."""
    lot = SalesLot.objects.create(
        event=event,
        lot_number="1",
        reserve_price=Money(100),
        status=SalesLot.STATUS_AVAILABLE,
        content_object=semen_batch,
        quantity=10,
        cost_at_creation=Money(100),
    )

    CommercialService.close_lot(lot, partner, Money(150), "2023-01-02")

    semen_batch.refresh_from_db()
    # 100 - 10 = 90
    assert semen_batch.current_quantity == 90


@pytest.mark.django_db
def test_close_lot_animal_status(event, bull, partner):
    """Test that closing an animal lot updates animal status."""
    lot = SalesLot.objects.create(
        event=event,
        lot_number="2",
        reserve_price=Money(1000),
        status=SalesLot.STATUS_AVAILABLE,
        cost_at_creation=Money(1000),
    )
    lot.animals.add(bull)

    CommercialService.close_lot(lot, partner, Money(1200), "2023-01-02")

    bull.refresh_from_db()
    assert bull.status == Cattle.STATUS_SOLD
