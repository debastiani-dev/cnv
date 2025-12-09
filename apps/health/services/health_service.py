from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.cattle.models import Cattle
from apps.health.models import SanitaryEvent, SanitaryEventTarget


class HealthService:
    @staticmethod
    @transaction.atomic
    def create_batch_event(
        event_data: Dict[str, Any], cattle_uuids: List[str]
    ) -> SanitaryEvent:
        """
        Creates a SanitaryEvent and links it to multiple cattle (targets).
        Calculates cost per head automatically.

        Args:
            event_data: Dict containing fields for SanitaryEvent (date, title,
                        medication, total_cost, performed_by, notes).
            cattle_uuids: List of Cattle UUID strings.
        """
        if not cattle_uuids:
            raise ValueError("No cattle selected for the event.")

        # 1. Create the Header (Event)
        event = SanitaryEvent.objects.create(**event_data)

        # 2. Calculate Cost Allocation
        total_cost = Decimal(event_data.get("total_cost", 0))
        cattle_count = len(cattle_uuids)
        cost_per_head = total_cost / cattle_count if cattle_count > 0 else Decimal(0)

        # Determine applied dose (use default if not provided in specific logic)
        # Note: If logic requires variable doses per animal, this would need
        # to be adapted. Here we assume uniform dose for the batch.
        applied_dose = None
        if event.medication:
            applied_dose = event.medication.default_dose

        # 3. Create Targets in Bulk
        targets = []
        for cattle_uuid in cattle_uuids:
            targets.append(
                SanitaryEventTarget(
                    event=event,
                    animal_id=cattle_uuid,
                    cost_per_head=cost_per_head,
                    applied_dose=applied_dose,
                )
            )

        SanitaryEventTarget.objects.bulk_create(targets)

        return event

    @staticmethod
    def check_withdrawal_status(animal: Cattle) -> Tuple[bool, Optional[str]]:
        """
        Checks if the animal is currently in a withdrawal period.

        Returns:
            Tuple (is_blocked: bool, reason: str | None)
        """
        today = timezone.localdate()

        # Optimization: Only look at events with medication in the recent past.
        # Assuming no withdrawal period exceeds 365 days, we can filter query.
        cutoff_date = today - timedelta(days=365)

        relevant_targets = SanitaryEventTarget.objects.filter(
            animal=animal,
            event__date__gte=cutoff_date,
            event__medication__isnull=False,
            event__is_deleted=False,
        ).select_related("event", "event__medication")

        for target in relevant_targets:
            medication = target.event.medication
            withdrawal_days = medication.withdrawal_days_meat

            if withdrawal_days > 0:
                event_date = target.event.date
                withdrawal_end_date = event_date + timedelta(days=withdrawal_days)

                if withdrawal_end_date > today:
                    reason = (
                        f"Animal in withdrawal period until {withdrawal_end_date.strftime('%Y-%m-%d')}. "
                        f"Medication: {medication.name} (Applied: {event_date.strftime('%Y-%m-%d')})"
                    )
                    return True, reason

        return False, None

    @staticmethod
    def get_animal_health_history(animal: Cattle):
        """
        Returns all health events for a specific animal, ordered by date.
        """
        return (
            SanitaryEventTarget.objects.filter(animal=animal, event__is_deleted=False)
            .select_related("event", "event__medication", "event__performed_by")
            .order_by("-event__date")
        )

    @staticmethod
    def get_active_withdrawal_count() -> int:
        """
        Returns the number of distinct active animals currently in a withdrawal period.
        """
        today = timezone.localdate()
        # Look back enough days to cover max withdrawal.
        # 365 days is a safe upper bound for most cattle meds.
        cutoff_date = today - timedelta(days=365)

        # 1. Fetch relevant targets (candidates)
        # We filter for active animals and events with medication that has withdrawal
        candidates = (
            SanitaryEventTarget.objects.filter(
                animal__status=Cattle.STATUS_AVAILABLE,
                event__date__gte=cutoff_date,
                event__is_deleted=False,
                event__medication__withdrawal_days_meat__gt=0,
            )
            .select_related("event", "event__medication")
            .values(
                "animal_id", "event__date", "event__medication__withdrawal_days_meat"
            )
        )

        # 2. Filter in Python to avoid complex DB Date math for now
        blocked_animal_ids = set()

        for item in candidates:
            animal_id = item["animal_id"]
            if animal_id in blocked_animal_ids:
                continue

            event_date = item["event__date"]
            days = item["event__medication__withdrawal_days_meat"]
            end_date = event_date + timedelta(days=days)

            if end_date > today:
                blocked_animal_ids.add(animal_id)

        return len(blocked_animal_ids)

    @staticmethod
    def get_deleted_events():
        """
        Returns all soft-deleted SanitaryEvents.
        """
        return (
            SanitaryEvent.all_objects.filter(is_deleted=True)
            .select_related("performed_by", "medication")
            .order_by("-modified_at")
        )

    @staticmethod
    @transaction.atomic
    def restore_event(event: SanitaryEvent) -> None:
        """
        Restores a soft-deleted event.
        """
        event.restore()

    @staticmethod
    @transaction.atomic
    def hard_delete_event(event: SanitaryEvent) -> None:
        """
        Permanently deletes an event.
        """
        event.delete(destroy=True)

    @staticmethod
    def get_recent_events(limit: int = 5):
        """
        Returns the most recent sanitary events.
        """
        return (
            SanitaryEvent.objects.annotate(target_count=Count("targets"))
            .select_related("medication")
            .order_by("-date", "-created_at")[:limit]
        )
