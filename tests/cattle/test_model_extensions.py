import pytest
from model_bakery import baker

from apps.cattle.models import Cattle


@pytest.mark.django_db
def test_cattle_sex_choices():
    # Test default
    c1 = baker.make(Cattle)
    assert c1.sex == Cattle.SEX_FEMALE

    # Test explicit
    c2 = baker.make(Cattle, sex=Cattle.SEX_MALE)
    assert c2.sex == Cattle.SEX_MALE


@pytest.mark.django_db
def test_cattle_parentage_hybrid():
    # 1. External Parent
    c1 = baker.make(Cattle, sire_external_id="External Bull 123", sire=None)
    assert c1.sire is None
    assert c1.sire_external_id == "External Bull 123"

    # 2. Internal Parent
    dad = baker.make(Cattle, tag="Internal Bull", sex=Cattle.SEX_MALE)
    c2 = baker.make(Cattle, sire=dad)
    assert c2.sire == dad
    # We don't enforce sire_external_id to be empty, but it's redundant.

    # 3. Offspring relation
    assert dad.offspring_sire.count() == 1
    assert dad.offspring_sire.first() == c2


@pytest.mark.django_db
def test_cattle_electronic_id_and_notes():
    c1 = baker.make(Cattle, electronic_id="RFID-999", notes="Some notes")
    assert c1.electronic_id == "RFID-999"
    assert c1.notes == "Some notes"


@pytest.mark.django_db
def test_cattle_parentage_constraints():
    # pylint: disable=import-outside-toplevel
    from django.core.exceptions import ValidationError

    # 1. Mutually Exclusive Sire
    dad = baker.make(Cattle, tag="Dad")
    c1 = Cattle(tag="ConflictSire", sire=dad, sire_external_id="External Conflict")
    with pytest.raises(ValidationError) as exc:
        c1.clean()
    assert "You cannot specify both an internal Sire and an external Sire ID" in str(
        exc.value
    )

    # 2. Mutually Exclusive Dam
    mom = baker.make(Cattle, tag="Mom")
    c2 = Cattle(tag="ConflictDam", dam=mom, dam_external_id="External Conflict")
    with pytest.raises(ValidationError) as exc:
        c2.clean()
    assert "You cannot specify both an internal Dam and an external Dam ID" in str(
        exc.value
    )

    # 3. No Self-Parentage (Sire)
    c3 = baker.make(Cattle, tag="SelfSire")
    c3.sire = c3
    with pytest.raises(ValidationError) as exc:
        c3.clean()
    assert "A cattle cannot be its own sire" in str(exc.value)

    # 4. No Self-Parentage (Dam)
    c4 = baker.make(Cattle, tag="SelfDam")
    c4.dam = c4
    with pytest.raises(ValidationError) as exc:
        c4.clean()
    assert "A cattle cannot be its own dam" in str(exc.value)
