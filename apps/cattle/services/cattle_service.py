from django.db.models import QuerySet
from apps.cattle.models import Cattle

class CattleService:
    @staticmethod
    def get_all_cattle(search_query: str = None) -> QuerySet[Cattle]:
        """
        Returns all cattle records ordered by tag.
        Optionally filters by tag or name if search_query is provided.
        """
        queryset = Cattle.objects.all().order_by("tag")
        
        if search_query:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(tag__icontains=search_query) | 
                Q(name__icontains=search_query)
            )
            
        return queryset

    @staticmethod
    def create_cattle(data: dict) -> Cattle:
        """Creates a new cattle record from valid data."""
        return Cattle.objects.create(**data)

    @staticmethod
    def update_cattle(cattle: Cattle, data: dict) -> Cattle:
        """Updates an existing cattle record."""
        for key, value in data.items():
            setattr(cattle, key, value)
        cattle.save()
        return cattle

    @staticmethod
    def get_deleted_cattle() -> QuerySet[Cattle]:
        """Returns all soft-deleted cattle records."""
        return Cattle.all_objects.filter(is_deleted=True).order_by("-modified_at")

    @staticmethod
    def restore_cattle(pk: int) -> Cattle:
        """
        Restores a soft-deleted cattle record.
        Raises ValueError if the tag is already in use by an active record.
        """
        cattle = Cattle.all_objects.get(pk=pk)
        
        # Check for conflict
        if Cattle.objects.filter(tag=cattle.tag).exists():
            raise ValueError(f"Cannot restore: Tag '{cattle.tag}' is already in use by an active record.")
            
        cattle.restore()
        return cattle
    
    @staticmethod
    def hard_delete_cattle(pk: int) -> None:
        """Permanently deletes a cattle record from the database."""
        cattle = Cattle.all_objects.get(pk=pk)
        cattle.delete(destroy=True)

    @staticmethod
    def delete_cattle(cattle: Cattle) -> None:
        """Soft-deletes a cattle record."""
        cattle.delete()
