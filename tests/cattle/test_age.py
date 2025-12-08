from datetime import date

import pytest
from model_bakery import baker

from apps.cattle.models import Cattle


@pytest.mark.django_db
def test_cattle_age_property():
    # 1. No birth date -> "-"
    c1 = baker.make(Cattle, birth_date=None)
    assert c1.age == "-"

    # 2. Exactly 1 year ago -> "1y 0m"
    today = date.today()
    c2 = baker.make(Cattle, birth_date=today.replace(year=today.year - 1))
    assert c2.age == "1y 0m"

    # Case: Same year, 5 months ago
    month = today.month - 5
    year = today.year
    if month <= 0:
        month += 12
        year -= 1

    if year == today.year:
        # e.g. May -> Jan
        c4 = baker.make(Cattle, birth_date=date(year, month, today.day))
        assert c4.age == "5m"
