from celery import shared_task
from django.core.management import call_command


@shared_task
def run_notification_scanners():
    """
    Periodic task to run all notification scanners.
    """
    call_command("scan_notifications")
