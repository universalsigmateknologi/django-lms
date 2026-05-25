from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Sum
from .models import Quiz, Question, Answer, EssayGrading


# ─── Inlines ─────────────────────────────────────────────────────────────────

class AnswerInline(admin.TabularInline):
    model         = Answer
    extra         = 4
    fields        = ("text", "is_correct", "order", "feedback")
    ordering      = ("order",)


class QuestionInline(admin.StackedInline):
    model            = Question
    extra            = 0
    fields           = (
        "question_type", "text", "points",
        "order", "explanation", "image",
        "code_language", "code_template",
    )
    ordering         = ("order",)
    show_change_link = True


# ─── ModelAdmin ──────────────────────────────────────────────────────────────

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display  = (
        "title", "lesson_title", "question_count_display",
        "total_points_display", "pass_score", "time_limit_fmt",
        "max_attempts", "is_active",
    )
    list_filter   = ("is_active", "randomize_questions", "show_feedback")
    search_fields = ("title", "lesson__title", "lesson__module__course__title")
    ordering      = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines       = [QuestionInline]

    fieldsets = (
        (_("Informasi Quiz"), {
            "fields": ("id", "lesson", "title", "description", "is_active"),
        }),
        (_("Aturan Pengerjaan"), {
            "fields": (
                "pass_score", "time_limit",
                "max_attempts", "show_feedback",
            ),
        }),
        (_("Randomisasi"), {
            "fields": ("randomize_questions", "randomize_answers"),
            "classes": ("collapse",),
        }),
        (_("Timestamp"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _q_count=Count("questions", distinct=True),
            _total_pts=Sum("questions__points"),
        )

    @admin.display(description="Lesson", ordering="lesson__title")
    def lesson_title(self, obj):
        return obj.lesson.title

    @admin.display(description="Questions", ordering="_q_count")
    def question_count_display(self, obj):
        return obj._q_count

    @admin.display(description="Total Points", ordering="_total_pts")
    def total_points_display(self, obj):
        return obj._total_pts or 0

    @admin.display(description="Time Limit")
    def time_limit_fmt(self, obj):
        if obj.time_limit == 0:
            return "∞ Unlimited"
        mins, secs = divmod(obj.time_limit, 60)
        return f"{mins:02d}:{secs:02d}"


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display  = (
        "short_text", "quiz_title", "question_type",
        "points", "order", "is_auto_graded_display", "created_at",
    )
    list_filter   = ("question_type",)
    search_fields = ("text", "quiz__title")
    ordering      = ("quiz", "order")
    readonly_fields = ("id", "created_at")
    inlines       = [AnswerInline]

    fieldsets = (
        (_("Soal"), {
            "fields": ("id", "quiz", "question_type", "text", "image"),
        }),
        (_("Poin & Urutan"), {
            "fields": ("points", "order"),
        }),
        (_("Feedback & Penjelasan"), {
            "fields": ("explanation",),
            "classes": ("collapse",),
        }),
        (_("Kode (Jika Tipe Code)"), {
            "fields": ("code_language", "code_template"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Question", ordering="text")
    def short_text(self, obj):
        return obj.text[:70] + "..." if len(obj.text) > 70 else obj.text

    @admin.display(description="Quiz", ordering="quiz__title")
    def quiz_title(self, obj):
        return obj.quiz.title

    @admin.display(description="Auto Grade?", boolean=True)
    def is_auto_graded_display(self, obj):
        return obj.is_auto_graded


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display  = ("short_text", "question_short", "is_correct", "order")
    list_filter   = ("is_correct",)
    search_fields = ("text", "question__text", "question__quiz__title")
    ordering      = ("question", "order")
    readonly_fields = ("id",)

    @admin.display(description="Answer", ordering="text")
    def short_text(self, obj):
        return obj.text[:70] + "..." if len(obj.text) > 70 else obj.text

    @admin.display(description="Question", ordering="question__text")
    def question_short(self, obj):
        return obj.question.text[:50]

@admin.register(EssayGrading)
class EssayGradingAdmin(admin.ModelAdmin):
    list_display  = ("student_email", "graded_by", "score", "has_feedback", "graded_at")
    list_filter   = ("graded_at",)
    search_fields = (
        "answer_record__attempt__enrollment__student__email",
        "graded_by__email",
    )
    readonly_fields = ("id", "answer_record", "graded_at")

    @admin.display(description="Student")
    def student_email(self, obj):
        return obj.answer_record.attempt.enrollment.student.email

    @admin.display(description="Feedback?", boolean=True)
    def has_feedback(self, obj):
        return bool(obj.feedback)

