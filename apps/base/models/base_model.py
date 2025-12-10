import uuid
from typing import Any, Optional, Union

from django.db import models
from django.db.models import ProtectedError
from django.utils.translation import gettext_lazy as _


class BaseQuerySet(models.QuerySet):
    """
    Custom QuerySet with soft deletion support.
    """

    def delete(self, destroy: bool = False) -> Union[int, tuple[int, dict[str, int]]]:
        """
        Soft delete items in the queryset unless destroy is True.
        """
        if not destroy:
            return (
                self.update(is_deleted=True),
                {"rows_updated": self.count()},
            )
        return super().delete()

    def soft_delete(self) -> int:
        """
        Mark items in the queryset as deleted.
        """
        return self.update(is_deleted=True)

    def restore(self) -> int:
        """
        Restore soft-deleted items in the queryset.
        """
        return self.update(is_deleted=False)


class BaseManager(models.Manager):
    """
    Manager that returns only non-deleted objects by default.
    """

    def get_queryset(self) -> BaseQuerySet:
        return BaseQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """
    Manager that returns all objects, including soft-deleted ones.
    """

    def get_queryset(self) -> BaseQuerySet:
        return BaseQuerySet(self.model, using=self._db)


class TimestampsOnlyBaseModel(models.Model):
    """
    Abstract base model with created_at and modified_at timestamps.
    Does NOT support soft deletion or UUIDs.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_("Modified at"))

    class Meta:
        abstract = True


class BaseModel(models.Model):
    """
    Abstract base model with UUID, timestamps, and soft deletion support.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_("Modified at"))
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        primary_key=True,
        verbose_name=_("uuid"),
        db_index=True,
    )
    is_deleted = models.BooleanField(default=False, db_index=True)

    objects = BaseManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Save the instance, updating the modified_at field.
        """
        update_fields = kwargs.get("update_fields", None)
        if update_fields:
            update_fields.append("modified_at")
        kwargs["update_fields"] = update_fields
        super().save(*args, **kwargs)

    def delete(
        self,
        using: Optional[str] = None,
        keep_parents: bool = False,
        destroy: bool = False,
    ) -> Any:  # type: ignore[override]
        """
        Soft delete the instance unless destroy is True.
        Enforces strict deletion rules: Cannot delete if referenced by other objects.
        """
        # Always check dependencies before ANY deletion (Soft or Hard)
        self._check_dependencies()

        if not destroy:
            return self.soft_delete()
        return models.Model.delete(self, using=using, keep_parents=keep_parents)

    def _check_dependencies(self) -> None:
        """
        Check for any reverse relations (generic check).
        Raises ProtectedError if related objects exist.
        """
        has_related_objects = False
        related_objects = []

        for rel in self._meta.get_fields(include_hidden=True):
            if not (
                (rel.one_to_many or rel.one_to_one)
                and rel.auto_created
                and not rel.concrete
            ):
                continue

            # mypy: rel is Union[Field, ForeignObjectRel, GenericForeignKey]
            # but we filtered for reverse relations which have get_accessor_name
            related_name = rel.get_accessor_name()  # type: ignore[union-attr]
            if not related_name:
                continue

            # Check if this relation is in the ignore list for strict deletion
            if related_name in getattr(self, "strict_deletion_ignore_fields", []):
                continue

            if not hasattr(self, related_name):
                continue

            manager = getattr(self, related_name)
            # Depending on relation type, it might be a Manager or single object
            if hasattr(manager, "exists"):
                if manager.exists():
                    has_related_objects = True
                    related_objects.extend(list(manager.all()))
            elif (
                manager is not None
            ):  # One-to-one reverse accessor returns object or None
                has_related_objects = True
                related_objects.append(manager)

        if has_related_objects:
            raise ProtectedError(
                str(
                    _(
                        "Cannot delete this object because it is referenced by other objects."
                    )
                ),
                set(related_objects),
            )

    def soft_delete(self) -> None:
        """
        Mark the instance as deleted.
        """
        self.is_deleted = True
        self.save()

    def restore(self) -> None:
        """
        Restore the soft-deleted instance.
        """
        self.is_deleted = False
        self.save()

    @property
    def deleted_date(self):
        """Returns modified_at as deleted_date if the object is deleted"""
        return self.modified_at if self.is_deleted else None
