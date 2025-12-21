from typing import Any

from django.db import models

from apps.genetics.models import EmbryoBatch, SemenBatch, StorageTank


class GeneticsService:
    """Service layer for genetics inventory management."""

    @staticmethod
    def get_all_tanks() -> Any:
        """Get all active storage tanks."""
        return StorageTank.objects.all().order_by("name")

    @staticmethod
    def get_deleted_tanks() -> Any:
        """Get all soft-deleted storage tanks."""
        return StorageTank.all_objects.filter(is_deleted=True).order_by("name")

    @staticmethod
    def delete_tank(tank: StorageTank) -> None:
        """Soft delete a storage tank."""
        tank.delete()

    @staticmethod
    def restore_tank(tank: StorageTank) -> None:
        """Restore a soft-deleted storage tank."""
        tank.restore()

    @staticmethod
    def hard_delete_tank(tank: StorageTank) -> None:
        """Permanently delete a storage tank."""
        tank.delete(destroy=True)

    @staticmethod
    def get_all_semen_batches() -> Any:
        """Get all active semen batches."""
        return SemenBatch.objects.select_related("bull", "tank", "supplier").order_by(
            "-purchase_date"
        )

    @staticmethod
    def get_deleted_semen_batches() -> Any:
        """Get all soft-deleted semen batches."""
        return (
            SemenBatch.all_objects.filter(is_deleted=True)
            .select_related("bull", "tank", "supplier")
            .order_by("-purchase_date")
        )

    @staticmethod
    def delete_semen_batch(batch: SemenBatch) -> None:
        """Soft delete a semen batch."""
        batch.delete()

    @staticmethod
    def restore_semen_batch(batch: SemenBatch) -> None:
        """Restore a soft-deleted semen batch."""
        batch.restore()

    @staticmethod
    def hard_delete_semen_batch(batch: SemenBatch) -> None:
        """Permanently delete a semen batch."""
        batch.delete(destroy=True)

    @staticmethod
    def get_all_embryo_batches() -> Any:
        """Get all active embryo batches."""
        return EmbryoBatch.objects.select_related("tank", "supplier").order_by(
            "-purchase_date"
        )

    @staticmethod
    def get_deleted_embryo_batches() -> Any:
        """Get all soft-deleted embryo batches."""
        return (
            EmbryoBatch.all_objects.filter(is_deleted=True)
            .select_related("tank", "supplier")
            .order_by("-purchase_date")
        )

    @staticmethod
    def delete_embryo_batch(batch: EmbryoBatch) -> None:
        """Soft delete an embryo batch."""
        batch.delete()

    @staticmethod
    def restore_embryo_batch(batch: EmbryoBatch) -> None:
        """Restore a soft-deleted embryo batch."""
        batch.restore()

    @staticmethod
    def hard_delete_embryo_batch(batch: EmbryoBatch) -> None:
        """Permanently delete an embryo batch."""
        batch.delete(destroy=True)

    @staticmethod
    def get_tank_inventory_summary(tank: StorageTank) -> dict:
        """Get inventory summary for a tank."""
        semen_batches = SemenBatch.objects.filter(tank=tank)
        embryo_batches = EmbryoBatch.objects.filter(tank=tank)

        return {
            "total_semen_doses": sum(b.current_quantity for b in semen_batches),
            "total_embryos": sum(b.current_quantity for b in embryo_batches),
            "semen_batches_count": semen_batches.count(),
            "embryo_batches_count": embryo_batches.count(),
            "low_stock_alerts": (
                semen_batches.filter(
                    current_quantity__lte=models.F("min_stock_alert")
                ).count()
                + embryo_batches.filter(
                    current_quantity__lte=models.F("min_stock_alert")
                ).count()
            ),
        }
