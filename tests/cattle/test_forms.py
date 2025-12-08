import pytest
from model_bakery import baker

from apps.cattle.forms import CattleForm
from apps.cattle.models import Cattle


@pytest.mark.django_db
class TestCattleForm:
    def test_duplicate_tag_invalid(self):
        # Create existing cattle
        baker.make(Cattle, tag="EXISTING", name="Original")

        # Try to validate form with same tag
        data = {
            "tag": "EXISTING",
            "name": "Duplicate",
            "breed": "Angus",
            "status": "available",
            "weight_kg": 500,
        }
        form = CattleForm(data=data)
        assert not form.is_valid()
        assert "Cattle with tag 'EXISTING' already exists." in form.errors["tag"]

    def test_duplicate_tag_allowed_if_deleted(self):
        # Create soft-deleted cattle
        c = baker.make(Cattle, tag="DELETED")
        c.delete()

        # Try to create new with same tag
        data = {
            "tag": "DELETED",
            "name": "New Version",
            "breed": "Angus",
            "status": "available",
            "weight_kg": 500,
        }
        form = CattleForm(data=data)
        assert form.is_valid()
