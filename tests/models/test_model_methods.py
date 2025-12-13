import pytest
from model_bakery import baker

from apps.cattle.models.cattle import Cattle
from apps.locations.models.location import Location
from apps.partners.models.partner import Partner


@pytest.mark.django_db
class TestModelMethods:
    def test_cattle_methods(self):
        c = baker.make(Cattle, tag="COW-001", status=Cattle.STATUS_AVAILABLE)
        # Test __str__
        assert str(c) == "COW-001 (Available)"
        # Test get_absolute_url
        assert c.get_absolute_url() == f"/cattle/{c.pk}/"

    def test_location_methods(self):
        lst = baker.make(Location, name="Paddock A")
        # Test __str__
        assert str(lst) == "Paddock A"
        # Test get_absolute_url
        assert lst.get_absolute_url() == f"/locations/{lst.pk}/"

    def test_partner_methods(self):
        p = baker.make(Partner, name="John Doe")
        # Test __str__
        assert str(p) == "John Doe"
        # Test get_absolute_url
        assert p.get_absolute_url() == f"/partners/{p.pk}/edit/"
