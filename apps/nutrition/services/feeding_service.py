from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.locations.models.location import Location
from apps.nutrition.models.diet import Diet
from apps.nutrition.models.event import FeedingEvent
from apps.nutrition.models.ingredient import FeedIngredient


class FeedingService:
    @staticmethod
    @transaction.atomic
    def record_feeding(
        location: Location,
        diet: Diet,
        amount_kg: Decimal,
        date,
        performed_by,
    ) -> FeedingEvent:
        """
        Records a feeding event, deducts inventory, and calculates simple costs.
        """
        if amount_kg <= 0:
            raise ValidationError(_("Feeding amount must be positive."))

        # 1. Validate Diet Composition
        diet_items = diet.items.select_related("ingredient").all()  # type: ignore
        if not diet_items.exists():
            raise ValidationError(_("Selected diet has no ingredients defined."))

        # Optional: Strict check for 100%? For now, we assume the recipe is correct
        # or we just use the proportions as they are (if it sums to 200%, it's 2x).
        # Let's assume standard behavior: proportion is "parts per 100" of the final mix.
        # So if I feed 100kg, and Corn is 50%, I use 50kg of Corn.

        # 2. Calculate Requirements & Check Stock
        ingredients_to_update = []
        total_cost = Decimal(0)

        for item in diet_items:
            required_qty = (amount_kg * item.proportion_percent) / Decimal(100)
            ingredient = item.ingredient

            if ingredient.stock_quantity < required_qty:
                raise ValidationError(
                    _(
                        "Insufficient stock for %(ingredient)s. Required: %(req).2f kg, Available: %(avail).2f kg"
                    )
                    % {
                        "ingredient": ingredient.name,
                        "req": required_qty,
                        "avail": ingredient.stock_quantity,
                    }
                )

            # Prepare update (in memory)
            ingredient.stock_quantity -= required_qty
            ingredients_to_update.append(ingredient)

            # Calculate cost snapshot
            total_cost += required_qty * ingredient.unit_cost

        # 3. Apply Inventory Updates
        FeedIngredient.objects.bulk_update(ingredients_to_update, ["stock_quantity"])

        # 4. Create Event
        event = FeedingEvent.objects.create(
            date=date,
            location=location,
            diet=diet,
            amount_kg=amount_kg,
            cost_total=total_cost,
            performed_by=performed_by,
        )

        return event
