import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class EnrollmentStatus(models.TextChoices):
    ACTIVE    = "active",    _("Active")
    COMPLETED = "completed", _("Completed")
    DROPPED   = "dropped",   _("Dropped")
    EXPIRED   = "expired",   _("Expired")


class Enrollment(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student      = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.CASCADE,
                     related_name="enrollments",
                     limit_choices_to={"role": "student"},
                   )
    course       = models.ForeignKey(
                     "courses.Course",
                     on_delete=models.CASCADE,
                     related_name="enrollments",
                   )
    status       = models.CharField(
                     _("status"), max_length=20,
                     choices=EnrollmentStatus.choices,
                     default=EnrollmentStatus.ACTIVE,
                   )
    progress_pct = models.FloatField(
                     _("progress percentage"), default=0.0,
                     validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                   )
    enrolled_at  = models.DateTimeField(_("enrolled at"), default=timezone.now)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    expired_at   = models.DateTimeField(_("expired at"), null=True, blank=True)
    order        = models.ForeignKey(
                     "payments.Order",
                     on_delete=models.SET_NULL,
                     null=True, blank=True,
                     related_name="enrollments",
                   )

    class Meta:
        db_table        = "enrollments"
        verbose_name    = _("enrollment")
        verbose_name_plural = _("enrollments")
        unique_together = ("student", "course")
        ordering        = ["-enrolled_at"]
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["course", "status"]),
        ]

    def __str__(self):
        return f"{self.student.email} → {self.course.title}"

    @property
    def is_active(self) -> bool:
        return self.status == EnrollmentStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        return self.status == EnrollmentStatus.COMPLETED

    def mark_completed(self):
        self.status       = EnrollmentStatus.COMPLETED
        self.progress_pct = 100.0
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "progress_pct", "completed_at"])

    def recalculate_progress(self):
        from apps.courses.models import Lesson
        total     = Lesson.objects.filter(module__course=self.course).count()
        completed = LessonProgress.objects.filter(enrollment=self, is_completed=True).count()

        if total == 0:
            self.progress_pct = 0.0
        else:
            self.progress_pct = round((completed / total) * 100, 2)

        if self.progress_pct >= 100.0:
            self.mark_completed()
        else:
            if self.status == EnrollmentStatus.COMPLETED:
                self.status = EnrollmentStatus.ACTIVE
                self.completed_at = None
                self.save(update_fields=["progress_pct", "status", "completed_at"])
            else:
                self.save(update_fields=["progress_pct"])


class LessonProgress(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment     = models.ForeignKey(
                       Enrollment,
                       on_delete=models.CASCADE,
                       related_name="lesson_progresses",
                     )
    lesson         = models.ForeignKey(
                       "courses.Lesson",
                       on_delete=models.CASCADE,
                       related_name="progresses",
                     )
    is_completed   = models.BooleanField(_("is completed"), default=False)
    last_position  = models.PositiveIntegerField(_("last position (sec)"), default=0)
    watch_duration = models.PositiveIntegerField(_("watch duration (sec)"), default=0)
    completed_at   = models.DateTimeField(_("completed at"), null=True, blank=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = "lesson_progresses"
        verbose_name    = _("lesson progress")
        verbose_name_plural = _("lesson progresses")
        unique_together = ("enrollment", "lesson")
        ordering        = ["lesson__order"]
        indexes = [
            models.Index(fields=["enrollment", "is_completed"]),
        ]

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.enrollment.student.email} | {self.lesson.title}"

    def mark_complete(self):
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save(update_fields=["is_completed", "completed_at"])
            self.enrollment.recalculate_progress()


class QuizAttempt(models.Model):
    class AttemptStatus(models.TextChoices):
        IN_PROGRESS = "in_progress", _("In Progress")
        PASSED      = "passed",      _("Passed")
        FAILED      = "failed",      _("Failed")

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment   = models.ForeignKey(
                     Enrollment,
                     on_delete=models.CASCADE,
                     related_name="quiz_attempts",
                   )
    quiz         = models.ForeignKey(
                     "quizzes.Quiz",
                     on_delete=models.CASCADE,
                     related_name="attempts",
                   )
    status       = models.CharField(
                     max_length=20,
                     choices=AttemptStatus.choices,
                     default=AttemptStatus.IN_PROGRESS,
                   )
    score        = models.FloatField(
                     _("score (%)"), default=0.0,
                     validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
                   )
    started_at   = models.DateTimeField(_("started at"), default=timezone.now)
    submitted_at = models.DateTimeField(_("submitted at"), null=True, blank=True)
    time_spent   = models.PositiveIntegerField(_("time spent (sec)"), default=0)

    class Meta:
        db_table     = "quiz_attempts"
        verbose_name = _("quiz attempt")
        verbose_name_plural = _("quiz attempts")
        ordering     = ["-started_at"]
        indexes = [
            models.Index(fields=["enrollment", "quiz"]),
        ]

    def __str__(self):
        return (
            f"{self.enrollment.student.email} | "
            f"{self.quiz.title} | Score: {self.score}%"
        )

    @property
    def is_passed(self) -> bool:
        return self.status == self.AttemptStatus.PASSED


class QuizAnswerRecord(models.Model):
    """
    Jawaban student per soal dalam satu QuizAttempt.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt         = models.ForeignKey(
                        QuizAttempt,
                        on_delete=models.CASCADE,
                        related_name="answer_records",
                      )
    question        = models.ForeignKey(
                        "quizzes.Question",
                        on_delete=models.CASCADE,
                        related_name="answer_records",
                      )
    # Untuk tipe multiple_choice dan true_false
    selected_answer = models.ForeignKey(
                        "quizzes.Answer",
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name="selected_records",
                      )
    # Untuk tipe essay dan code
    text_answer     = models.TextField(_("text answer"), blank=True)
    is_correct      = models.BooleanField(_("is correct"), default=False)

    class Meta:
        db_table        = "quiz_answer_records"
        verbose_name    = _("quiz answer record")
        verbose_name_plural = _("quiz answer records")
        unique_together = ("attempt", "question")

    def __str__(self):
        mark = "✓" if self.is_correct else "✗"
        return f"{mark} {self.attempt.enrollment.student.email} | Q: {self.question.text[:40]}"