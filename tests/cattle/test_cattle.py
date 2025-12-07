import pytest
from model_bakery import baker

from apps.cattle.models import Cattle, Sale, SaleItem


@pytest.mark.django_db
class TestCattleModel:
    def test_create_cattle(self):
        cattle = baker.make(Cattle, tag="TAG-001", status=Cattle.STATUS_AVAILABLE)
        assert cattle.tag == "TAG-001"
        assert cattle.status == "available"
        assert str(cattle) == "TAG-001 (Available)"

    def test_soft_delete(self):
        cattle = baker.make(Cattle)
        cattle_id = cattle.id
        cattle.delete()

        assert cattle.is_deleted
        assert cattle.deleted_date is not None

        # Default manager should not return it
        assert not Cattle.objects.filter(id=cattle_id).exists()

        # AllObjects manager should return it
        assert Cattle.all_objects.filter(id=cattle_id).exists()


@pytest.mark.django_db
class TestSaleModel:
    def test_create_sale(self):
        sale = baker.make(Sale, buyer="John Doe", total_price=1000.00)
        assert sale.buyer == "John Doe"
        assert sale.total_price == 1000.00

    def test_sale_item(self):
        sale = baker.make(Sale)
        cattle = baker.make(Cattle)
        item = baker.make(SaleItem, sale=sale, cattle=cattle, price=500.00)

        assert item.sale == sale
        assert item.cattle == cattle
        assert item.price == 500.00
