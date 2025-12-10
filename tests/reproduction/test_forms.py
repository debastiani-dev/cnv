import pytest
from django.utils import timezone

from apps.cattle.models.cattle import Cattle
from apps.reproduction.forms import (
    BreedingEventForm,
    CalvingForm,
    ReproductiveSeasonForm,
)
from apps.reproduction.models import BreedingEvent, Calving


@pytest.mark.django_db
class TestReproductiveSeasonForm:
    def test_valid_form(self):
        data = {
            "name": "Test Season",
            "start_date": timezone.now().date(),
            "end_date": (timezone.now() + timezone.timedelta(days=90)).date(),
            "active": True,
        }
        form = ReproductiveSeasonForm(data=data)
        assert form.is_valid()

    def test_invalid_form_missing_required(self):
        data = {}
        form = ReproductiveSeasonForm(data=data)
        assert not form.is_valid()
        assert "name" in form.errors
        assert "start_date" in form.errors


@pytest.mark.django_db
class TestBreedingEventForm:
    def test_valid_form(self):
        cow = Cattle.objects.create(
            tag="COW001",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            status=Cattle.STATUS_AVAILABLE,
        )
        data = {
            "dam": cow.pk,
            "date": timezone.now().date(),
            "breeding_method": BreedingEvent.METHOD_AI,
            "sire_name": "Bull 1",
        }
        form = BreedingEventForm(data=data)
        assert form.is_valid()

    def test_queryset_filtering(self):
        # Create cows with different statuses
        open_cow = Cattle.objects.create(
            tag="OPEN",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            status=Cattle.STATUS_AVAILABLE,
        )
        pregnant_cow = Cattle.objects.create(
            tag="PREG",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
        )

        form = BreedingEventForm()
        queryset = form.fields["dam"].queryset

        assert open_cow in queryset
        assert pregnant_cow not in queryset


@pytest.mark.django_db
class TestCalvingForm:
    def test_valid_form(self):
        cow = Cattle.objects.create(
            tag="COW002",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
        )
        # Create a breeding event linked to the cow
        breeding = BreedingEvent.objects.create(
            dam=cow,
            date=timezone.now() - timezone.timedelta(days=280),
            breeding_method=BreedingEvent.METHOD_AI,
        )

        data = {
            "dam": cow.pk,
            "breeding_event": breeding.pk,
            "date": timezone.now().date(),
            "ease_of_birth": Calving.EASE_EASY,
            "calf_tag": "CALF001",
            "calf_sex": Cattle.SEX_MALE,
            "calf_weight": 35.5,
        }
        form = CalvingForm(data=data)
        assert form.is_valid(), form.errors

    def test_queryset_filtering(self):
        pregnant_cow = Cattle.objects.create(
            tag="PREG2",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_PREGNANT,
            status=Cattle.STATUS_AVAILABLE,
        )
        open_cow = Cattle.objects.create(
            tag="OPEN2",
            sex=Cattle.SEX_FEMALE,
            reproduction_status=Cattle.REP_STATUS_OPEN,
            status=Cattle.STATUS_AVAILABLE,
        )

        form = CalvingForm()
        queryset = form.fields["dam"].queryset

        assert pregnant_cow in queryset
        assert open_cow not in queryset
