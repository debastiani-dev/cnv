from datetime import datetime
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.authentication.models import User
from apps.cattle.models import Cattle
from apps.locations.models import Location, Movement


class MovementService:
    @staticmethod
    @transaction.atomic
    def move_cattle(
        cattle_list: List[Cattle],
        destination: Location,
        performed_by: User,
        reason: str,
        move_date: Optional[datetime] = None,
        origin: Optional[Location] = None,
        notes: str = "",
    ) -> Movement:
        """
        Moves a list of cattle to a new destination.
        Creates a Movement record and updates each animal's location.

        Args:
            cattle_list: List of Cattle instances to move.
            destination: Target Location.
            performed_by: User performing the action.
            reason: MovementReason choice.
            move_date: Optional date of movement (defaults to now).
            origin: Optional explicit origin (defaults to cattle's current location).
                   Note: If cattle have mixed origins, this might be ambiguous.
                   Ideally, batch movers come from same place, but 'origin' on Movement
                   is singular. If mixed, we might leave origin null or use first?
                   For simplicity, we assume bulk move implies same origin or we leave
                   Motion.origin as logic dictates (e.g. from common pasture).
            notes: Optional text notes.

        Returns:
            The created Movement instance.
        """
        if not move_date:
            move_date = timezone.now()

        # 1. Validation
        if not destination.is_active:
            raise ValidationError(_("Cannot move cattle to an inactive location."))

        if destination.status == "RESTING":
            # Just a warning? Or strict block?
            # User requirement says "Alert if RESTING location has animals".
            # We allow it but maybe the UI warns.
            pass

        # Detect Origin if not provided
        # If all cattle come from same location, set it. Otherwise Null?
        if not origin:
            first_loc = cattle_list[0].location
            # Check if all in same loc
            if all(c.location == first_loc for c in cattle_list):
                origin = first_loc

        # 2. Create Movement Record
        movement = Movement.objects.create(
            date=move_date,
            origin=origin,
            destination=destination,
            reason=reason,
            performed_by=performed_by,
            notes=notes,
        )
        movement.animals.set(cattle_list)

        # 3. Update Inventory
        for animal in cattle_list:
            animal.location = destination
            animal.save(update_fields=["location", "modified_at"])

        return movement
