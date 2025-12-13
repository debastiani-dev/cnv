# pylint: disable=unused-argument
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.health.models import SanitaryEvent
from apps.reproduction.models import BreedingEvent, PregnancyCheck
from apps.tasks.services.tasks import TaskService


@receiver(post_save, sender=BreedingEvent)
def trigger_breeding_tasks(sender, instance, created, **kwargs):
    if created:
        TaskService.handle_breeding_event(instance)


@receiver(post_save, sender=PregnancyCheck)
def trigger_pregnancy_tasks(sender, instance, created, **kwargs):
    if created:
        TaskService.handle_pregnancy_check(instance)


@receiver(post_save, sender=SanitaryEvent)
def trigger_sanitary_tasks(sender, instance, created, **kwargs):
    if created:
        TaskService.handle_sanitary_event(instance)
