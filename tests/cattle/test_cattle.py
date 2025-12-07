from apps.base.utils.money import Money
from apps.cattle.services.cattle_service import CattleService
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
        sale = baker.make(Sale, buyer="John Doe", total_price=Money(1000.00))
        assert sale.buyer == "John Doe"
        assert sale.total_price == Money(1000.00)

    def test_sale_item(self):
        sale = baker.make(Sale)
        cattle = baker.make(Cattle)
        item = baker.make(SaleItem, sale=sale, cattle=cattle, price=Money(500.00))

        assert item.sale == sale
        assert item.cattle == cattle
        assert item.price == Money(500.00)


@pytest.mark.django_db
class TestCattleService:
    def test_restore_cattle(self):
        cattle = baker.make(Cattle)
        cattle.delete()  # Soft delete
        assert cattle.is_deleted

        restored_cattle = CattleService.restore_cattle(cattle.pk)
        assert not restored_cattle.is_deleted
        assert restored_cattle.status == Cattle.STATUS_AVAILABLE

    def test_restore_conflict_prevention(self):
        # 1. Create and delete "TAG-X"
        cattle_deleted = baker.make(Cattle, tag="TAG-X")
        cattle_deleted.delete()

        # 2. Create active "TAG-X"
        baker.make(Cattle, tag="TAG-X")

        # 3. Try to restore original -> Should fail
        with pytest.raises(ValueError, match="already in use"):
            CattleService.restore_cattle(cattle_deleted.pk)

    def test_hard_delete_cattle(self):
        cattle = baker.make(Cattle)
        pk = cattle.pk
        
        # Soft delete first (as usually happens)
        cattle.delete()
        
        # Hard delete
        CattleService.hard_delete_cattle(pk)
        
        # Verify completely gone
        assert not Cattle.all_objects.filter(pk=pk).exists()

    def test_reuse_tag_after_soft_delete(self):
        # 1. Create and soft delete
        c1 = baker.make(Cattle, tag="TAG-REUSE")
        c1.delete()
        
        # 2. Create new with same tag -> Should succeed
        c2 = baker.make(Cattle, tag="TAG-REUSE")
        assert c2.pk != c1.pk
        assert not c2.is_deleted
