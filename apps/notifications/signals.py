from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.enrollments.models import Enrollment, EnrollmentStatus
from apps.certificates.models import Certificate
from apps.discussions.models import Reply
from .models import Notification, NotificationType


@receiver(post_save, sender=Enrollment)
def notify_enrollment(sender, instance, created, **kwargs):
    """Notifikasi saat enrollment baru dibuat."""
    if not created:
        return
    Notification.objects.create(
        recipient=instance.student,
        notification_type=NotificationType.ENROLLMENT_SUCCESS,
        title="Enrollment Berhasil!",
        message=f"Selamat! Kamu berhasil mendaftar kursus '{instance.course.title}'.",
        action_url=f"/courses/{instance.course.slug}/learn/",
    )


@receiver(post_save, sender=Enrollment)
def notify_course_completed(sender, instance, **kwargs):
    """Notifikasi saat kursus selesai."""
    if instance.status != EnrollmentStatus.COMPLETED:
        return
    Notification.objects.create(
        recipient=instance.student,
        notification_type=NotificationType.COURSE_COMPLETED,
        title="Kursus Selesai!",
        message=f"Kamu telah menyelesaikan kursus '{instance.course.title}'. Sertifikat sedang disiapkan.",
        action_url=f"/courses/{instance.course.slug}/",
    )


@receiver(post_save, sender=Certificate)
def notify_certificate_issued(sender, instance, created, **kwargs):
    """Notifikasi saat sertifikat diterbitkan."""
    if not created:
        return
    Notification.objects.create(
        recipient=instance.student,
        notification_type=NotificationType.CERTIFICATE_ISSUED,
        title="Sertifikat Diterbitkan!",
        message=f"Sertifikatmu untuk kursus '{instance.course_title_snapshot}' sudah siap diunduh.",
        action_url=f"/certificates/{instance.certificate_number}/",
    )


@receiver(post_save, sender=Reply)
def notify_discussion_reply(sender, instance, created, **kwargs):
    """Notifikasi ke author discussion saat ada reply baru."""
    if not created:
        return
    discussion = instance.discussion
    # Jangan notifikasi jika author reply adalah author discussion itu sendiri
    if instance.author == discussion.author:
        return
    Notification.objects.create(
        recipient=discussion.author,
        actor=instance.author,
        notification_type=NotificationType.DISCUSSION_REPLY,
        title="Ada Reply Baru!",
        message=f"{instance.author.full_name or instance.author.username} membalas diskusimu: '{discussion.title[:60]}'.",
        action_url=f"/discussions/{discussion.id}/",
    )