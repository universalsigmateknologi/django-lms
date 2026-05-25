import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class CertificateTemplate(models.Model):
    """
    Template desain sertifikat — bisa berbeda per kursus.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(_("template name"), max_length=100)
    # File HTML/CSS template atau file gambar background
    html_template = models.TextField(
                      _("html template"), blank=True,
                      help_text=_("Template HTML dengan placeholder {{student_name}}, {{course_title}}, dll"),
                    )
    background  = models.ImageField(
                    _("background image"),
                    upload_to="certificates/templates/",
                    null=True, blank=True,
                  )
    is_default  = models.BooleanField(_("is default"), default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = "certificate_templates"
        verbose_name = _("certificate template")
        verbose_name_plural = _("certificate templates")
        ordering     = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Pastikan hanya satu template yang jadi default
        if self.is_default:
            CertificateTemplate.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Certificate(models.Model):
    """
    Sertifikat yang diterbitkan otomatis saat enrollment selesai 100%.
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Nomor sertifikat unik untuk verifikasi publik
    certificate_number = models.CharField(
                           _("certificate number"),
                           max_length=30, unique=True, editable=False,
                         )
    student        = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.CASCADE,
                       related_name="certificates",
                       limit_choices_to={"role": "student"},
                     )
    course         = models.ForeignKey(
                       "courses.Course",
                       on_delete=models.CASCADE,
                       related_name="certificates",
                     )
    enrollment     = models.OneToOneField(
                       "enrollments.Enrollment",
                       on_delete=models.CASCADE,
                       related_name="certificate",
                     )
    template       = models.ForeignKey(
                       CertificateTemplate,
                       on_delete=models.SET_NULL,
                       null=True, blank=True,
                       related_name="certificates",
                     )
    # Snapshot data saat sertifikat diterbitkan
    student_name_snapshot = models.CharField(
                              _("student name snapshot"), max_length=150,
                            )
    course_title_snapshot = models.CharField(
                              _("course title snapshot"), max_length=255,
                            )
    instructor_name_snapshot = models.CharField(
                                 _("instructor name snapshot"), max_length=150,
                               )
    # File PDF hasil generate
    pdf_file       = models.FileField(
                       _("pdf file"),
                       upload_to="certificates/pdf/",
                       null=True, blank=True,
                     )
    issued_at      = models.DateTimeField(_("issued at"), default=timezone.now)
    is_valid       = models.BooleanField(_("is valid"), default=True)
    revoked_at     = models.DateTimeField(_("revoked at"), null=True, blank=True)
    revoke_reason  = models.TextField(_("revoke reason"), blank=True)

    class Meta:
        db_table        = "certificates"
        verbose_name    = _("certificate")
        verbose_name_plural = _("certificates")
        unique_together = ("student", "course")
        ordering        = ["-issued_at"]
        indexes         = [
            models.Index(fields=["certificate_number"]),
            models.Index(fields=["student", "is_valid"]),
        ]

    def __str__(self):
        return f"{self.certificate_number} | {self.student_name_snapshot}"

    def save(self, *args, **kwargs):
        # Auto-generate certificate number
        if not self.certificate_number:
            self.certificate_number = self._generate_cert_number()
        # Auto-snapshot data
        if not self.student_name_snapshot:
            # Menggunakan get_full_name() atau username jika tidak tersedia
            self.student_name_snapshot = getattr(self.student, 'get_full_name', lambda: self.student.username)()
        if not self.course_title_snapshot:
            self.course_title_snapshot = self.course.title
        if not self.instructor_name_snapshot:
            self.instructor_name_snapshot = getattr(self.course.instructor, 'get_full_name', lambda: self.course.instructor.username)()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_cert_number() -> str:
        import random, string
        prefix = timezone.now().strftime("%Y%m")
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"CERT-{prefix}-{suffix}"

    @property
    def verification_url(self) -> str:
        from django.urls import reverse
        return reverse("certificates:verify", kwargs={"cert_number": self.certificate_number})

    @property
    def is_accessible(self) -> bool:
        """
        Sertifikat dapat diakses jika:
        1. Course.is_lesson_finished == True
        2. Enrollment.progress_pct == 100.0
        """
        return self.course.is_lesson_finished and self.enrollment.progress_pct >= 100.0

    def revoke(self, reason: str = ""):
        """Cabut sertifikat — misal jika terjadi kecurangan."""
        self.is_valid     = False
        self.revoked_at   = timezone.now()
        self.revoke_reason = reason
        self.save(update_fields=["is_valid", "revoked_at", "revoke_reason"])