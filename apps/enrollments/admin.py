from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Enrollment, LessonProgress, QuizAttempt, QuizAnswerRecord
from apps.enrollments.models import EnrollmentStatus


# ─── Inlines ─────────────────────────────────────────────────────────────────

class LessonProgressInline(admin.TabularInline):
    model            = LessonProgress
    extra            = 0
    readonly_fields  = (
        "lesson", "is_completed", "last_position",
        "watch_duration", "completed_at", "updated_at",
    )
    can_delete       = False
    show_change_link = True


class QuizAttemptInline(admin.TabularInline):
    model            = QuizAttempt
    extra            = 0
    readonly_fields  = (
        "quiz", "status", "score",
        "started_at", "submitted_at", "time_spent",
    )
    can_delete       = False
    show_change_link = True


class QuizAnswerRecordInline(admin.TabularInline):
    model           = QuizAnswerRecord
    extra           = 0
    readonly_fields = ("question", "selected_answer", "text_answer", "is_correct")
    can_delete      = False


# ─── ModelAdmin ──────────────────────────────────────────────────────────────

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display    = (
        "student_email", "course_title", "status_badge",
        "progress_bar", "enrolled_at", "completed_at",
    )
    list_filter     = ("status", "enrolled_at")
    search_fields   = ("student__email", "student__username", "course__title")
    ordering        = ("-enrolled_at",)
    readonly_fields = ("id", "enrolled_at", "completed_at", "progress_pct")
    autocomplete_fields = ("student", "course")
    inlines         = [LessonProgressInline, QuizAttemptInline]

    fieldsets = (
        (_("Relasi"), {
            "fields": ("id", "student", "course", "order"),
        }),
        (_("Status & Progress"), {
            "fields": ("status", "progress_pct"),
        }),
        (_("Timestamp"), {
            "fields": ("enrolled_at", "completed_at", "expired_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Student", ordering="student__email")
    def student_email(self, obj):
        return obj.student.email

    @admin.display(description="Course", ordering="course__title")
    def course_title(self, obj):
        return obj.course.title

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "active":    ("#1D9E75", "#E8F5E9"),
            "completed": ("#378ADD", "#EAF3FB"),
            "dropped":   ("#7F8C8D", "#F2F3F4"),
            "expired":   ("#C0392B", "#FDEDEC"),
        }
        color, bg = colors.get(obj.status, ("#555", "#eee"))
        return format_html(
            '<span style="background:{bg};color:{color};padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:500;">{label}</span>',
            bg=bg, color=color, label=obj.get_status_display(),
        )

    @admin.display(description="Progress")
    def progress_bar(self, obj):
        pct   = int(obj.progress_pct)
        color = "#1D9E75" if pct >= 100 else "#378ADD" if pct > 0 else "#ccc"
        return format_html(
            '<div style="width:120px;background:#eee;border-radius:4px;">'
            '<div style="width:{pct}%;background:{color};border-radius:4px;'
            'text-align:center;color:#fff;font-size:11px;min-width:28px;">'
            '{pct}%</div></div>',
            pct=pct, color=color,
        )

    actions = ["mark_as_completed", "mark_as_dropped"]

    @admin.action(description="Tandai sebagai Completed")
    def mark_as_completed(self, request, queryset):
        for enrollment in queryset:
            enrollment.mark_completed()
        self.message_user(request, f"{queryset.count()} enrollment ditandai completed.")

    @admin.action(description="Tandai sebagai Dropped")
    def mark_as_dropped(self, request, queryset):
        queryset.update(status=EnrollmentStatus.DROPPED)
        self.message_user(request, f"{queryset.count()} enrollment ditandai dropped.")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display  = (
        "student_email", "course_title", "lesson_title",
        "is_completed", "last_position_fmt",
        "watch_duration_fmt", "updated_at",
    )
    list_filter   = ("is_completed",)
    search_fields = (
        "enrollment__student__email",
        "enrollment__course__title",
        "lesson__title",
    )
    ordering      = ("-updated_at",)
    readonly_fields = ("id", "completed_at", "updated_at")

    @admin.display(description="Student", ordering="enrollment__student__email")
    def student_email(self, obj):
        return obj.enrollment.student.email

    @admin.display(description="Course")
    def course_title(self, obj):
        return obj.enrollment.course.title

    @admin.display(description="Lesson", ordering="lesson__title")
    def lesson_title(self, obj):
        return obj.lesson.title

    @admin.display(description="Last Position")
    def last_position_fmt(self, obj):
        mins, secs = divmod(obj.last_position, 60)
        return f"{mins:02d}:{secs:02d}"

    @admin.display(description="Watch Duration")
    def watch_duration_fmt(self, obj):
        mins, secs = divmod(obj.watch_duration, 60)
        return f"{mins:02d}:{secs:02d}"


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display  = (
        "student_email", "quiz_title", "status",
        "score", "time_spent_fmt",
        "started_at", "submitted_at",
    )
    list_filter   = ("status",)
    search_fields = ("enrollment__student__email", "quiz__title")
    ordering      = ("-started_at",)
    readonly_fields = ("id", "started_at", "submitted_at", "time_spent")
    inlines       = [QuizAnswerRecordInline]

    fieldsets = (
        (_("Relasi"), {
            "fields": ("id", "enrollment", "quiz"),
        }),
        (_("Hasil"), {
            "fields": ("status", "score"),
        }),
        (_("Waktu"), {
            "fields": ("started_at", "submitted_at", "time_spent"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Student")
    def student_email(self, obj):
        return obj.enrollment.student.email

    @admin.display(description="Quiz", ordering="quiz__title")
    def quiz_title(self, obj):
        return obj.quiz.title

    @admin.display(description="Time Spent")
    def time_spent_fmt(self, obj):
        mins, secs = divmod(obj.time_spent, 60)
        return f"{mins:02d}:{secs:02d}"


@admin.register(QuizAnswerRecord)
class QuizAnswerRecordAdmin(admin.ModelAdmin):
    list_display  = (
        "student_email", "question_short",
        "selected_answer", "is_correct",
    )
    list_filter   = ("is_correct",)
    search_fields = (
        "attempt__enrollment__student__email",
        "question__text",
    )
    readonly_fields = ("id",)

    @admin.display(description="Student")
    def student_email(self, obj):
        return obj.attempt.enrollment.student.email

    @admin.display(description="Question")
    def question_short(self, obj):
        return obj.question.text[:60]