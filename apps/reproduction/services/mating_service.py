from django.db.models import QuerySet

from apps.reproduction.models import MatingPlan


class MatingPlanService:
    """
    Service for managing Mating Plans, including soft deletion and restore.
    """

    @staticmethod
    def get_all_plans() -> QuerySet[MatingPlan]:
        """
        Returns all active Mating Plans.
        """
        return (
            MatingPlan.objects.select_related("season", "sire")
            .prefetch_related("cows")
            .order_by("-season", "sire__name")
        )

    @staticmethod
    def create_plan(data: dict) -> MatingPlan:
        """
        Creates a new Mating Plan.
        """
        # Form logic handles m2m if using form.save(), but here we might need manual handling if passing raw dict.
        # However, views usually call form.save().
        # For consistency with CattleService pattern (which takes data dict), we'd do MatingPlan.objects.create(**data).
        # But M2M fields (cows) can't be passed to create directly.
        # So we'll let the View/Form handle creation or adapt this.
        # For now, let's just assume this method is for strict 'create' calls, assuming cows are set later or handled separately.
        # Actually, simpler to just have the view use the form for creation,
        # but the Trash/Restore logic definitely needs the service.
        raise NotImplementedError("Use form for creation")

    @staticmethod
    def get_deleted_plans() -> QuerySet[MatingPlan]:
        """Returns all soft-deleted mating plans."""
        return MatingPlan.all_objects.filter(is_deleted=True).order_by("-modified_at")

    @staticmethod
    def restore_plan(pk: int) -> MatingPlan:
        """
        Restores a soft-deleted mating plan.
        """
        plan = MatingPlan.all_objects.get(pk=pk)
        plan.restore()
        return plan

    @staticmethod
    def hard_delete_plan(pk: int) -> None:
        """Permanently deletes a mating plan from the database."""
        plan = MatingPlan.all_objects.get(pk=pk)
        plan.delete(destroy=True)

    @staticmethod
    def delete_plan(plan: MatingPlan) -> None:
        """Soft-deletes a mating plan."""
        plan.delete()
