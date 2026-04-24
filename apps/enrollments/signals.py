from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import LessonProgress


@receiver(post_save, sender=LessonProgress)
def update_enrollment_progress(sender, instance, **kwargs):
    instance.enrollment.recalculate_progress()