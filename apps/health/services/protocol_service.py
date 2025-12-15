from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.cattle.models import Cattle
from apps.health.models import HealthProtocol, SanitaryEvent, SanitaryEventTarget


class ProtocolService:
    @staticmethod
    def apply_protocol(
        protocol_id, target_cattle_ids, date=None, performed_by=None, notes=""
    ):
        """
        Applies a Health Protocol to a list of cattle.
        Creates one SanitaryEvent per ProtocolItem, and targets all selected cattle.
        """
        if not target_cattle_ids:
            raise ValidationError("No cattle selected for protocol application.")

        try:
            protocol = HealthProtocol.objects.get(pk=protocol_id)
        except HealthProtocol.DoesNotExist as e:
            raise ValidationError("Health Protocol not found.") from e

        if not protocol.is_active:
            raise ValidationError("Cannot apply an inactive protocol.")

        items = protocol.items.all()
        if not items.exists():
            raise ValidationError("This protocol has no items/medications defined.")

        if date is None:
            date = timezone.now().date()

        created_events = []

        with transaction.atomic():
            # fetch cattle objects to ensure validity and passed to subsequent services if needed
            cattle_list = list(Cattle.objects.filter(pk__in=target_cattle_ids))

            if len(cattle_list) != len(target_cattle_ids):
                # This check effectively filters out invalid IDs, but we might want to warn
                pass

            for item in items:
                event = ProtocolService._create_event_and_targets(
                    protocol, item, cattle_list, date, performed_by, notes
                )
                created_events.append(event)

        return {
            "protocol": protocol.name,
            "events_created": len(created_events),
            "cattle_count": len(target_cattle_ids),
            "total_records": len(created_events) * len(target_cattle_ids),
        }

    @staticmethod
    def _create_event_and_targets(
        protocol, item, cattle_list, date, performed_by, base_notes
    ):
        """
        Helper to create a single SanitaryEvent and its Targets for the batch.
        Also handles withdrawal period updates.
        """
        # Create the Header Event (e.g., "Vaccination - Ivermectin")
        event_notes = f"Via Protocol: {protocol.name}. {base_notes}".strip()
        if item.notes:
            event_notes += f" ({item.notes})"

        title_str = f"{protocol.name} - {item.medication.name if item.medication else 'Procedure'}"
        if len(title_str) > 150:
            title_str = title_str[:147] + "..."

        event = SanitaryEvent.objects.create(
            date=date,
            title=title_str,
            medication=item.medication,
            total_cost=0,
            performed_by=performed_by,
            notes=event_notes,
        )

        # Create Targets (The Batch)
        targets = []
        for cattle in cattle_list:
            targets.append(
                SanitaryEventTarget(
                    event=event,
                    animal=cattle,
                    observation=f"Dosage: {item.default_dosage}",
                )
            )

        SanitaryEventTarget.objects.bulk_create(targets)

        # Trigger Side Effects (Withdrawal periods)
        if item.medication and (
            item.medication.withdrawal_days_meat > 0
            or item.medication.withdrawal_days_milk > 0
        ):
            withdrawal_days = max(
                item.medication.withdrawal_days_meat,
                item.medication.withdrawal_days_milk,
            )
            withdrawal_end_date = date + timezone.timedelta(days=withdrawal_days)

            for cattle in cattle_list:
                if (
                    not cattle.withdrawal_end_date
                    or withdrawal_end_date > cattle.withdrawal_end_date
                ):
                    cattle.withdrawal_end_date = withdrawal_end_date
                    cattle.save(update_fields=["withdrawal_end_date"])

        return event
