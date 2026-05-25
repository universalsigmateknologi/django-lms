import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class NotificationType(models.TextChoices):
    # Enrollment
    ENROLLMENT_SUCCESS  = "enrollment_success",  _("Enrollment Success")
    COURSE_COMPLETED    = "course_completed",     _("Course Completed")
    # Certificate
    CERTIFICATE_ISSUED  = "certificate_issued",   _("Certificate Issued")
    CERTIFICATE_REVOKED = "certificate_revoked",  _("Certificate Revoked")
    # Quiz
    QUIZ_PASSED         = "quiz_passed",          _("Quiz Passed")
    QUIZ_FAILED         = "quiz_failed",          _("Quiz Failed")
    ESSAY_GRADED        = "essay_graded",         _("Essay Graded")
    # Discussion
    DISCUSSION_REPLY    = "discussion_reply",     _("New Reply on Discussion")
    REPLY_ACCEPTED      = "reply_accepted",       _("Reply Accepted as Answer")
    DISCUSSION_FLAGGED  = "discussion_flagged",   _("Discussion Flagged")
    # Payment
    PAYMENT_SUCCESS     = "payment_success",      _("Payment Success")
    PAYMENT_FAILED      = "payment_failed",       _("Payment Failed")
    REFUND_APPROVED     = "refund_approved",      _("Refund Approved")
    REFUND_REJECTED     = "refund_rejected",      _("Refund Rejected")
    # Course management
    COURSE_APPROVED     = "course_approved",      _("Course Approved")
    COURSE_REJECTED     = "course_rejected",      _("Course Rejected")
    COURSE_NEW_REVIEW   = "course_new_review",    _("New Review on Course")
    # System
    ANNOUNCEMENT        = "announcement",         _("Announcement")


class Notification(models.Model):
    """
    In-app notification untuk setiap user.
    Dibuat via signal atau Celery task.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient     = models.ForeignKey(
                      settings.AUTH_USER_MODEL,
                      on_delete=models.CASCADE,
                      related_name="notifications",
                    )
    # Aktor — siapa yang memicu notifikasi (bisa null jika sistem)
    actor         = models.ForeignKey(
                      settings.AUTH_USER_MODEL,
                      on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name="triggered_notifications",
                    )
    notification_type = models.CharField(
                          _("type"), max_length=30,
                          choices=NotificationType.choices,
                        )
    title         = models.CharField(_("title"), max_length=255)
    message       = models.TextField(_("message"))
    # URL tujuan saat notifikasi diklik
    action_url    = models.CharField(_("action url"), max_length=500, blank=True)
    is_read       = models.BooleanField(_("is read"), default=False)
    read_at       = models.DateTimeField(_("read at"), null=True, blank=True)
    created_at    = models.DateTimeField(_("created at"), default=timezone.now)

    class Meta:
        db_table     = "notifications"
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering     = ["-created_at"]
        indexes      = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self):
        return f"[{self.notification_type}] → {self.recipient.email}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    @classmethod
    def mark_all_read(cls, user):
        cls.objects.filter(
            recipient=user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())


class EmailNotification(models.Model):
    """
    Queue email yang dikirim via Celery task.
    Menyimpan status pengiriman untuk audit dan retry.
    """
    class EmailStatus(models.TextChoices):
        PENDING   = "pending",   _("Pending")
        SENT      = "sent",      _("Sent")
        FAILED    = "failed",    _("Failed")
        CANCELLED = "cancelled", _("Cancelled")

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient    = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.CASCADE,
                     related_name="email_notifications",
                   )
    # Relasi opsional ke in-app notification
    notification = models.OneToOneField(
                     Notification,
                     on_delete=models.SET_NULL,
                     null=True, blank=True,
                     related_name="email_notification",
                   )
    subject      = models.CharField(_("subject"), max_length=255)
    body_html    = models.TextField(_("body html"))
    body_text    = models.TextField(_("body text"), blank=True)
    status       = models.CharField(
                     _("status"), max_length=20,
                     choices=EmailStatus.choices,
                     default=EmailStatus.PENDING,
                   )
    # Jumlah percobaan kirim
    retry_count  = models.PositiveSmallIntegerField(_("retry count"), default=0)
    max_retries  = models.PositiveSmallIntegerField(_("max retries"), default=3)
    error_log    = models.TextField(_("error log"), blank=True)
    scheduled_at = models.DateTimeField(
                     _("scheduled at"), default=timezone.now,
                     help_text=_("Waktu email dijadwalkan untuk dikirim"),
                   )
    sent_at      = models.DateTimeField(_("sent at"), null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = "email_notifications"
        verbose_name = _("email notification")
        verbose_name_plural = _("email notifications")
        ordering     = ["-created_at"]
        indexes      = [
            models.Index(fields=["status", "scheduled_at"]),
            models.Index(fields=["recipient", "status"]),
        ]

    def __str__(self):
        return f"[{self.status}] {self.subject} → {self.recipient.email}"

    def mark_sent(self):
        self.status  = self.EmailStatus.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at"])

    def mark_failed(self, error: str = ""):
        self.status     = self.EmailStatus.FAILED
        self.retry_count += 1
        self.error_log  = error
        self.save(update_fields=["status", "retry_count", "error_log"])

    @property
    def can_retry(self) -> bool:
        return (
            self.status == self.EmailStatus.FAILED and
            self.retry_count < self.max_retries
        )


class NotificationPreference(models.Model):
    """
    Preferensi notifikasi per user — bisa disable tipe tertentu.
    """
    user              = models.OneToOneField(
                          settings.AUTH_USER_MODEL,
                          on_delete=models.CASCADE,
                          related_name="notification_preference",
                        )
    # In-app
    in_app_enabled    = models.BooleanField(_("in-app notifications"), default=True)
    # Email
    email_enabled     = models.BooleanField(_("email notifications"), default=True)
    email_enrollment  = models.BooleanField(_("email on enrollment"), default=True)
    email_quiz        = models.BooleanField(_("email on quiz result"), default=True)
    email_discussion  = models.BooleanField(_("email on discussion reply"), default=True)
    email_payment     = models.BooleanField(_("email on payment"), default=True)
    email_certificate = models.BooleanField(_("email on certificate"), default=True)
    # Weekly digest
    weekly_digest     = models.BooleanField(_("weekly digest email"), default=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = "notification_preferences"
        verbose_name = _("notification preference")
        verbose_name_plural = _("notification preferences")

    def __str__(self):
        return f"Preferences of {self.user.email}"