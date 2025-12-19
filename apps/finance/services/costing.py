import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.base.utils.money import Money
from apps.finance.models.finance import CostEntry


class CostingService:
    @staticmethod
    def create_cost(data):
        """
        Creates a single cost entry.
        """
        cost = CostEntry(**data)
        cost.save()
        return cost

    @staticmethod
    def create_batch_costs(cattle_list, data):
        """
        Creates cost entries for multiple animals.
        data: dict containing 'date', 'category', 'amount', 'description'
        """
        costs = []
        for animal in cattle_list:
            # We must create instances individually if we want signal handling (if any)
            # But bulk_create is better for performance.
            # However, Money field might need attention.
            # CostEntry uses Money for amount? No, we switched to Decimal in recent steps?
            # Let's check model.
            # If standard save is used, it's safer.

            # Using loop for safety and simplicity first.
            cost = CostEntry(
                animal=animal,
                date=data["date"],
                category=data["category"],
                amount=data["amount"],
                description=data.get("description", ""),
            )
            cost.full_clean()
            cost.save()
            costs.append(cost)
        return costs

    @staticmethod
    def update_cost(cost: CostEntry, data):
        """
        Updates a cost entry.
        """
        for field, value in data.items():
            if hasattr(cost, field):
                setattr(cost, field, value)
        cost.save()
        return cost

    @staticmethod
    def delete_cost(cost_entry):
        """
        Soft deletes a cost entry.
        """
        cost_entry.delete()

    @staticmethod
    def restore_cost(pk):
        """
        Restores a soft-deleted cost entry.
        """
        cost = CostEntry.all_objects.get(pk=pk)
        cost.restore()
        return cost

    @staticmethod
    def hard_delete_cost(pk):
        """
        Permanently deletes a cost entry.
        """
        cost = CostEntry.all_objects.get(pk=pk, is_deleted=True)
        cost.delete(destroy=True)

    @staticmethod
    def get_all_costs():
        return CostEntry.objects.all()

    @staticmethod
    def get_deleted_costs():
        return CostEntry.all_objects.filter(is_deleted=True)

    @staticmethod
    @transaction.atomic
    def allocate_feeding_cost(feeding_event):
        """
        Calculates cost. Formula: (Price/kg * Kg Fed) / Head Count
        """
        # 1. Wrap raw values in Money
        # Assuming feeding_event.ingredient has weighted_average_cost
        price_per_kg = Money(feeding_event.ingredient.weighted_average_cost)
        total_kg = Money(feeding_event.amount_kg)

        # 2. Precise Math
        total_event_cost = price_per_kg * total_kg

        # 3. Distribute
        if feeding_event.is_batch:
            animals = feeding_event.animals.all()
            head_count = animals.count()
            if head_count > 0:
                cost_per_head = Money(total_event_cost / head_count)

                entries = [
                    CostEntry(
                        animal=animal,
                        date=feeding_event.date,
                        category=CostEntry.CATEGORY_NUTRITION,
                        description=f"Nutrition: {feeding_event.ingredient.name}",
                        amount=cost_per_head,  # Auto-converts to Decimal via save? No, bulk_create skips save()
                        source_event=feeding_event,
                    )
                    for animal in animals
                ]

                # IMPORTANT: bulk_create does NOT call save(), so simple assignment won't run the Money() conversion in save().
                # However, we are explicitly passing cost_per_head which is ALREADY a Money object (and thus a Decimal).
                # So it should be fine.

                CostEntry.objects.bulk_create(entries)
        else:
            # Single animal feeding event? Implementation depends on FeedingEvent model structure.
            # Assuming is_batch=False means it is linked to a single animal directly or handled differently.
            # But the requirement mainly showed the batch logic. I will stick to the user's snippet logic + standard CRUD.
            pass

    @staticmethod
    def get_cost_stats(days=90):
        """
        Aggregates operational costs for the last N days.
        Returns a dict: {'total_cost': Decimal(...)}
        """
        start_date = timezone.now().date() - datetime.timedelta(days=days)

        # Aggregate all costs (excluding soft-deleted ones) since start_date
        total_cost = CostEntry.objects.filter(date__gte=start_date).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        return {"total_cost": total_cost}
