from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import LessonProgress


@receiver(post_save, sender=LessonProgress)
def update_enrollment_progress(sender, instance, **kwargs):
    instance.enrollment.recalculate_progress()


@receiver(post_save, sender="courses.Lesson")
@receiver(post_delete, sender="courses.Lesson")
def update_all_enrollments_on_lesson_change(sender, instance, **kwargs):
    """
    Jika ada materi baru ditambahkan atau dihapus, 
    update progress semua student yang terdaftar di kursus tersebut.
    """
    from .models import Enrollment
    course = instance.module.course
    enrollments = Enrollment.objects.filter(course=course)
    for enrollment in enrollments:
        enrollment.recalculate_progress()