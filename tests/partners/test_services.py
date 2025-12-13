import pytest
from model_bakery import baker

from apps.base.utils.money import Money
from apps.partners.models import Partner
from apps.partners.services.partner_service import PartnerService
from apps.purchases.models import Purchase
from apps.sales.models import Sale


@pytest.mark.django_db
class TestPartnerServiceAnnotations:
    def test_get_partners_annotations(self):
        # 1. Partner with no sales/purchases
        baker.make(Partner, name="Empty Partner")

        # 2. Partner with Sales
        p2 = baker.make(Partner, name="Sales Partner")
        baker.make(Sale, partner=p2, total_amount=Money(100))
        baker.make(Sale, partner=p2, total_amount=Money(50))

        # 3. Partner with Purchases
        p3 = baker.make(Partner, name="Purchases Partner")
        baker.make(Purchase, partner=p3, total_amount=Money(200))

        # 4. Partner with Both
        p4 = baker.make(Partner, name="Both Partner")
        baker.make(Sale, partner=p4, total_amount=Money(30))
        baker.make(Purchase, partner=p4, total_amount=Money(10))

        # Act
        partners = PartnerService.get_partners()
        p_map = {p.name: p for p in partners}

        # Assert
        assert p_map["Empty Partner"].total_sales == 0
        assert p_map["Empty Partner"].total_purchases == 0

        assert p_map["Sales Partner"].total_sales == 150
        assert p_map["Sales Partner"].total_purchases == 0

        assert p_map["Purchases Partner"].total_sales == 0
        assert p_map["Purchases Partner"].total_purchases == 200

        assert p_map["Both Partner"].total_sales == 30
        assert p_map["Both Partner"].total_purchases == 10


@pytest.mark.django_db
class TestPartnerServiceCRUD:
    def test_create_partner(self):
        data = {
            "name": "Service Created",
            "is_supplier": True,
            "email": "service@example.com",
        }
        partner = PartnerService.create_partner(data)
        assert partner.pk
        assert partner.name == "Service Created"

    def test_update_partner(self):
        partner = baker.make(Partner, name="Old Name")
        data = {"name": "New Name"}
        updated = PartnerService.update_partner(partner, data)
        updated.refresh_from_db()
        assert updated.name == "New Name"

    def test_delete_and_restore(self):
        partner = baker.make(Partner)
        PartnerService.delete_partner(partner)
        assert partner.is_deleted

        deleted = PartnerService.get_deleted_partners()
        assert partner in deleted

        PartnerService.restore_partner(partner)
        partner.refresh_from_db()
        assert not partner.is_deleted

    def test_hard_delete(self):
        partner = baker.make(Partner)
        partner.delete()

        PartnerService.hard_delete_partner(partner)
        assert not Partner.all_objects.filter(pk=partner.pk).exists()
