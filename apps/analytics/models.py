import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class CourseAnalytic(models.Model):
    """
    Snapshot harian statistik per kursus.
    Di-update via Celery Beat setiap hari.
    """
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course              = models.ForeignKey(
                            "courses.Course",
                            on_delete=models.CASCADE,
                            related_name="analytics",
                          )
    date                = models.DateField(_("date"), default=timezone.now)
    # Enrollment
    total_enrollments   = models.PositiveIntegerField(_("total enrollments"), default=0)
    new_enrollments     = models.PositiveIntegerField(_("new enrollments today"), default=0)
    total_completions   = models.PositiveIntegerField(_("total completions"), default=0)
    new_completions     = models.PositiveIntegerField(_("new completions today"), default=0)
    # Progress
    avg_progress_pct    = models.FloatField(_("average progress (%)"), default=0.0)
    completion_rate     = models.FloatField(_("completion rate (%)"), default=0.0)
    drop_rate           = models.FloatField(_("drop rate (%)"), default=0.0)
    # Revenue
    total_revenue       = models.DecimalField(
                            _("total revenue"), max_digits=14,
                            decimal_places=2, default=0,
                          )
    new_revenue         = models.DecimalField(
                            _("new revenue today"), max_digits=14,
                            decimal_places=2, default=0,
                          )
    # Rating
    avg_rating          = models.FloatField(_("average rating"), default=0.0)
    total_reviews       = models.PositiveIntegerField(_("total reviews"), default=0)
    # Discussion
    total_discussions   = models.PositiveIntegerField(_("total discussions"), default=0)
    total_replies       = models.PositiveIntegerField(_("total replies"), default=0)

    class Meta:
        db_table        = "course_analytics"
        verbose_name    = _("course analytic")
        verbose_name_plural = _("course analytics")
        unique_together = ("course", "date")
        ordering        = ["-date"]
        indexes         = [
            models.Index(fields=["course", "date"]),
        ]

    def __str__(self):
        return f"{self.course.title} | {self.date}"


class InstructorAnalytic(models.Model):
    """
    Snapshot harian statistik per instruktur.
    """
    id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instructor        = models.ForeignKey(
                          settings.AUTH_USER_MODEL,
                          on_delete=models.CASCADE,
                          related_name="analytics",
                          limit_choices_to={"role": "instructor"},
                        )
    date              = models.DateField(_("date"), default=timezone.now)
    total_courses     = models.PositiveIntegerField(_("total courses"), default=0)
    published_courses = models.PositiveIntegerField(_("published courses"), default=0)
    total_students    = models.PositiveIntegerField(_("total students"), default=0)
    new_students      = models.PositiveIntegerField(_("new students today"), default=0)
    total_revenue     = models.DecimalField(
                          _("total revenue"), max_digits=14,
                          decimal_places=2, default=0,
                        )
    new_revenue       = models.DecimalField(
                          _("new revenue today"), max_digits=14,
                          decimal_places=2, default=0,
                        )
    avg_rating        = models.FloatField(_("average rating across courses"), default=0.0)
    total_completions = models.PositiveIntegerField(_("total completions"), default=0)

    class Meta:
        db_table        = "instructor_analytics"
        verbose_name    = _("instructor analytic")
        verbose_name_plural = _("instructor analytics")
        unique_together = ("instructor", "date")
        ordering        = ["-date"]
        indexes         = [
            models.Index(fields=["instructor", "date"]),
        ]

    def __str__(self):
        return f"{self.instructor.email} | {self.date}"


class PlatformAnalytic(models.Model):
    """
    Snapshot harian statistik keseluruhan platform.
    Hanya satu record per hari.
    """
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date                = models.DateField(_("date"), unique=True, default=timezone.now)
    # User
    total_users         = models.PositiveIntegerField(_("total users"), default=0)
    new_users           = models.PositiveIntegerField(_("new users today"), default=0)
    total_students      = models.PositiveIntegerField(_("total students"), default=0)
    total_instructors   = models.PositiveIntegerField(_("total instructors"), default=0)
    active_users        = models.PositiveIntegerField(
                            _("active users today"), default=0,
                            help_text=_("User yang login hari ini"),
                          )
    # Course
    total_courses       = models.PositiveIntegerField(_("total courses"), default=0)
    published_courses   = models.PositiveIntegerField(_("published courses"), default=0)
    new_courses         = models.PositiveIntegerField(_("new courses today"), default=0)
    # Enrollment
    total_enrollments   = models.PositiveIntegerField(_("total enrollments"), default=0)
    new_enrollments     = models.PositiveIntegerField(_("new enrollments today"), default=0)
    total_completions   = models.PositiveIntegerField(_("total completions"), default=0)
    # Revenue
    total_revenue       = models.DecimalField(
                            _("total revenue"), max_digits=16,
                            decimal_places=2, default=0,
                          )
    new_revenue         = models.DecimalField(
                            _("new revenue today"), max_digits=16,
                            decimal_places=2, default=0,
                          )
    # Quiz
    total_quiz_attempts = models.PositiveIntegerField(_("total quiz attempts"), default=0)
    quiz_pass_rate      = models.FloatField(_("quiz pass rate (%)"), default=0.0)
    # Certificate
    total_certificates  = models.PositiveIntegerField(_("total certificates issued"), default=0)
    new_certificates    = models.PositiveIntegerField(_("new certificates today"), default=0)

    class Meta:
        db_table     = "platform_analytics"
        verbose_name = _("platform analytic")
        verbose_name_plural = _("platform analytics")
        ordering     = ["-date"]

    def __str__(self):
        return f"Platform | {self.date}"


class UserActivityLog(models.Model):
    """
    Log aktivitas user — login, tonton video, kerjakan quiz, dll.
    Digunakan untuk heatmap aktivitas dan analitik detail.
    """
    class ActivityType(models.TextChoices):
        LOGIN           = "login",           _("Login")
        LOGOUT          = "logout",          _("Logout")
        WATCH_VIDEO     = "watch_video",     _("Watch Video")
        COMPLETE_LESSON = "complete_lesson", _("Complete Lesson")
        SUBMIT_QUIZ     = "submit_quiz",     _("Submit Quiz")
        POST_DISCUSSION = "post_discussion", _("Post Discussion")
        POST_REPLY      = "post_reply",      _("Post Reply")
        ENROLL_COURSE   = "enroll_course",   _("Enroll Course")
        COMPLETE_COURSE = "complete_course", _("Complete Course")
        DOWNLOAD_CERT   = "download_cert",   _("Download Certificate")

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(
                      settings.AUTH_USER_MODEL,
                      on_delete=models.CASCADE,
                      related_name="activity_logs",
                    )
    activity_type = models.CharField(
                      _("activity type"), max_length=30,
                      choices=ActivityType.choices,
                    )
    # Referensi objek terkait — opsional
    course        = models.ForeignKey(
                      "courses.Course",
                      on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name="activity_logs",
                    )
    lesson        = models.ForeignKey(
                      "courses.Lesson",
                      on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name="activity_logs",
                    )
    # Metadata tambahan — IP, device, durasi, dll
    metadata      = models.JSONField(_("metadata"), default=dict, blank=True)
    ip_address    = models.GenericIPAddressField(_("ip address"), null=True, blank=True)
    user_agent    = models.TextField(_("user agent"), blank=True)
    created_at    = models.DateTimeField(_("created at"), default=timezone.now)

    class Meta:
        db_table     = "user_activity_logs"
        verbose_name = _("user activity log")
        verbose_name_plural = _("user activity logs")
        ordering     = ["-created_at"]
        indexes      = [
            models.Index(fields=["user", "activity_type"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["course", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} | {self.activity_type} | {self.created_at:%Y-%m-%d %H:%M}"