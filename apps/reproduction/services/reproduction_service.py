from datetime import timedelta

from django.db import transaction
from django.utils.translation import gettext as _

from apps.cattle.models.cattle import Cattle
from apps.reproduction.models import BreedingEvent, Calving, PregnancyCheck


class ReproductionService:
    GESTATION_DAYS = 290  # Average for Nelore/Zebu

    @staticmethod
    def calculate_due_date(breeding_date):
        """Calculates expected calving date based on breeding date."""
        if not breeding_date:
            return None
        return breeding_date + timedelta(days=ReproductionService.GESTATION_DAYS)

    @staticmethod
    @transaction.atomic
    def record_breeding(dam, date, method, sire=None, sire_name="", batch=None):
        """
        Records a breeding event and updates the cow's status.
        """
        if dam.sex != Cattle.SEX_FEMALE:
            raise ValueError(_("Only female cattle can be bred."))

        event = BreedingEvent.objects.create(
            dam=dam,
            date=date,
            breeding_method=method,
            sire=sire,
            sire_name=sire_name,
            batch=batch,
        )

        # Update Cow Status
        dam.reproduction_status = Cattle.REP_STATUS_BRED
        dam.save()

        return event

    @staticmethod
    @transaction.atomic
    def record_diagnosis(breeding_event, date, result, fetus_days=None):
        """
        Records a pregnancy check and updates the cow's status.
        """
        # Calculate expected calving date if positive
        expected_date = None
        if result == PregnancyCheck.RESULT_POSITIVE:
            # If fetus days provided, use that for more accuracy
            if fetus_days:
                # Approximate conception date = diagnosis_date - fetus_days
                conception_date = date - timedelta(days=fetus_days)
                expected_date = conception_date + timedelta(
                    days=ReproductionService.GESTATION_DAYS
                )
            else:
                expected_date = ReproductionService.calculate_due_date(
                    breeding_event.date
                )

        check = PregnancyCheck.objects.create(
            breeding_event=breeding_event,
            date=date,
            result=result,
            fetus_days=fetus_days,
            expected_calving_date=expected_date,
        )

        # Update Cow Status
        dam = breeding_event.dam
        if result == PregnancyCheck.RESULT_POSITIVE:
            dam.reproduction_status = Cattle.REP_STATUS_PREGNANT
        else:
            dam.reproduction_status = Cattle.REP_STATUS_OPEN
        dam.save()

        return check

    @staticmethod
    @transaction.atomic
    def register_birth(
        dam, date, breeding_event, calf_data, ease_of_birth=Calving.EASE_EASY, notes=""
    ):
        """
        Records a birth, updates dam status explanation, and auto-creates the calf.
        calf_data expected dict: {'tag': '...', 'sex': '...', 'weight_kg': ...}
        """
        # 1. Create Calving Record
        calving = Calving.objects.create(
            dam=dam,
            breeding_event=breeding_event,
            date=date,
            ease_of_birth=ease_of_birth,
            notes=notes,
        )

        # 2. Auto-Create Calf (The Engine Room Logic)
        sire = breeding_event.sire if breeding_event else None
        sire_name = breeding_event.sire_name if breeding_event else ""

        calf = Cattle.objects.create(
            tag=calf_data.get("tag"),
            name=calf_data.get("name", ""),
            sex=calf_data.get(
                "sex", Cattle.SEX_FEMALE
            ),  # Default to female or require it?
            birth_date=date,
            weight_kg=calf_data.get("weight_kg"),
            dam=dam,
            sire=sire,
            sire_external_id=sire_name or "",
            reproduction_status=(
                Cattle.REP_STATUS_OPEN
                if calf_data.get("sex") == Cattle.SEX_FEMALE
                else ""
            ),  # Open if female
            status=Cattle.STATUS_AVAILABLE,  # "CALF_AT_FOOT" was requested, using AVAILABLE for now as per choices
        )

        # Link calf to calving
        calving.calf = calf
        calving.save()

        # 3. Update Dam Status
        dam.reproduction_status = Cattle.REP_STATUS_LACTATING
        dam.save()

        return calving, calf

    @staticmethod
    def get_deleted_breeding_events():
        """
        Returns all soft-deleted BreedingEvents.
        """
        return (
            BreedingEvent.all_objects.filter(is_deleted=True)
            .select_related("dam", "sire")
            .order_by("-modified_at")
        )

    @staticmethod
    @transaction.atomic
    def restore_breeding_event(pk: str) -> None:
        """
        Restores a soft-deleted breeding event.
        """
        event = BreedingEvent.all_objects.get(pk=pk)
        event.restore()

    @staticmethod
    @transaction.atomic
    def hard_delete_breeding_event(pk: str) -> None:
        """
        Permanently deletes a breeding event.
        """
        event = BreedingEvent.all_objects.get(pk=pk)
        event.delete(destroy=True)
