import pytest
from django.contrib.admin import AdminSite
from model_bakery import baker

from apps.cattle.models import Cattle
from apps.commercial.admin import SalesLotAdmin
from apps.commercial.models import SalesEvent, SalesLot


@pytest.mark.django_db
def test_sales_lot_admin_animals_count():
    event = baker.make(SalesEvent)
    lot = baker.make(SalesLot, event=event)
    animals = baker.make(Cattle, _quantity=3)
    lot.animals.set(animals)

    site = AdminSite()
    admin = SalesLotAdmin(SalesLot, site)

    assert admin.animals_count(lot) == 3
