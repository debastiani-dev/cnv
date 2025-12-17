from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.services.scanners.calf_weaning import CalfWeaningScanner
from apps.notifications.services.scanners.low_stock import LowStockScanner
from apps.notifications.services.scanners.medication_expiry import (
    MedicationExpiryScanner,
)
from apps.notifications.services.scanners.pregnancy_check import PregnancyCheckScanner
from apps.notifications.services.scanners.task_due import TaskDueScanner
from apps.notifications.services.scanners.withdrawal_end import WithdrawalEndScanner


class Command(BaseCommand):
    help = "Scans system state and generates notifications for various conditions."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f"Starting notification scan at {timezone.now()}...")
        )

        scanners = [
            LowStockScanner(),
            TaskDueScanner(),
            PregnancyCheckScanner(),
            # New Scanners
            MedicationExpiryScanner(),
            WithdrawalEndScanner(),
            CalfWeaningScanner(),
        ]

        total_created = 0

        for scanner in scanners:
            try:
                scanner_name = scanner.__class__.__name__
                count = scanner.scan()
                total_created += count
                if count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{scanner_name}: Created {count} notifications."
                        )
                    )
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.stdout.write(
                    self.style.ERROR(f"Error running {scanner_name}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Scan complete. Total notifications created: {total_created}"
            )
        )
