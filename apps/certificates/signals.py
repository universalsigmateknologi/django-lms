from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.enrollments.models import Enrollment, EnrollmentStatus
from .models import Certificate, CertificateTemplate


@receiver(post_save, sender=Enrollment)
def auto_generate_certificate(sender, instance, **kwargs):
    """
    Otomatis buat sertifikat saat enrollment berstatus completed
    dan belum punya sertifikat sebelumnya.
    """
    if instance.status != EnrollmentStatus.COMPLETED:
        return

    already_exists = Certificate.objects.filter(
        student=instance.student,
        course=instance.course,
    ).exists()

    if already_exists:
        return

    # Ambil template default jika ada
    template = CertificateTemplate.objects.filter(is_default=True).first()

    Certificate.objects.create(
        student=instance.student,
        course=instance.course,
        enrollment=instance,
        template=template,
    )