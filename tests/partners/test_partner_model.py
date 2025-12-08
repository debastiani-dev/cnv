import pytest
from model_bakery import baker

from apps.partners.models import Partner


@pytest.mark.django_db
class TestPartnerModel:
    def test_create_partner(self):
        partner = baker.make(Partner, name="Agro Corp", tax_id="12345678000199")
        assert Partner.objects.count() == 1
        assert partner.name == "Agro Corp"
        assert str(partner) == "Agro Corp"

    def test_default_values(self):
        partner = baker.make(Partner)
        assert partner.is_customer is True
        assert partner.is_supplier is False
