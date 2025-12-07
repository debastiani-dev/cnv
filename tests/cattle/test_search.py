import pytest
from model_bakery import baker
from apps.cattle.models import Cattle
from apps.cattle.services.cattle_service import CattleService

@pytest.mark.django_db
class TestCattleSearch:
    def test_search_by_tag(self):
        # Create cattle
        baker.make(Cattle, tag="ALPHA-001", name="Alpha")
        baker.make(Cattle, tag="BETA-002", name="Beta")
        
        # Search "ALPHA"
        results = CattleService.get_all_cattle(search_query="ALPHA")
        assert results.count() == 1
        assert results.first().tag == "ALPHA-001"

    def test_search_by_name(self):
        baker.make(Cattle, tag="TAG-1", name="Charlie One")
        baker.make(Cattle, tag="TAG-2", name="Charlie Two")
        baker.make(Cattle, tag="TAG-3", name="Delta")
        
        # Search "Charlie"
        results = CattleService.get_all_cattle(search_query="Charlie")
        assert results.count() == 2
        
    def test_search_empty(self):
        baker.make(Cattle, _quantity=3)
        results = CattleService.get_all_cattle(search_query="")
        assert results.count() == 3

    def test_search_no_match(self):
        baker.make(Cattle, tag="TAG-001")
        results = CattleService.get_all_cattle(search_query="ZULU")
        assert results.count() == 0
