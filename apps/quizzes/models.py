import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class QuestionType(models.TextChoices):
    MULTIPLE_CHOICE = "multiple_choice", _("Multiple Choice")
    TRUE_FALSE      = "true_false",      _("True / False")
    ESSAY           = "essay",           _("Essay")
    CODE            = "code",            _("Code")


class Quiz(models.Model):
    """
    Satu Quiz melekat pada satu Lesson bertipe 'quiz'.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson        = models.OneToOneField(
                      "courses.Lesson",
                      on_delete=models.CASCADE,
                      related_name="quiz",
                    )
    title         = models.CharField(_("title"), max_length=200)
    description   = models.TextField(_("description"), blank=True)
    pass_score    = models.PositiveSmallIntegerField(
                      _("pass score (%)"), default=70,
                      validators=[MinValueValidator(1), MaxValueValidator(100)],
                    )
    time_limit    = models.PositiveIntegerField(
                      _("time limit (seconds)"), default=0,
                      help_text=_("0 = tidak ada batas waktu"),
                    )
    max_attempts  = models.PositiveSmallIntegerField(
                      _("max attempts"), default=0,
                      help_text=_("0 = tidak terbatas"),
                    )
    randomize_questions = models.BooleanField(_("randomize questions"), default=False)
    randomize_answers   = models.BooleanField(_("randomize answers"), default=False)
    show_feedback       = models.BooleanField(
                            _("show feedback after submit"), default=True,
                          )
    is_active     = models.BooleanField(_("is active"), default=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = "quizzes"
        verbose_name = _("quiz")
        verbose_name_plural = _("quizzes")

    def __str__(self):
        return f"Quiz: {self.title}"

    @property
    def question_count(self) -> int:
        return self.questions.count()

    @property
    def total_points(self) -> int:
        return self.questions.aggregate(
            total=models.Sum("points")
        )["total"] or 0


class Question(models.Model):
    """
    Satu soal dalam sebuah Quiz.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz          = models.ForeignKey(
                      Quiz,
                      on_delete=models.CASCADE,
                      related_name="questions",
                    )
    question_type = models.CharField(
                      _("question type"), max_length=20,
                      choices=QuestionType.choices,
                      default=QuestionType.MULTIPLE_CHOICE,
                    )
    text          = models.TextField(_("question text"))
    explanation   = models.TextField(
                      _("explanation"), blank=True,
                      help_text=_("Ditampilkan setelah student menjawab"),
                    )
    points        = models.PositiveSmallIntegerField(_("points"), default=1)
    order         = models.PositiveSmallIntegerField(_("order"), default=0)
    image         = models.ImageField(
                      upload_to="quiz/questions/",
                      null=True, blank=True,
                    )
    # Khusus tipe CODE
    code_language = models.CharField(
                      _("code language"), max_length=30,
                      blank=True,
                      help_text=_("Contoh: python, javascript, sql"),
                    )
    code_template = models.TextField(
                      _("code template"), blank=True,
                      help_text=_("Kode awal yang ditampilkan di editor"),
                    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = "quiz_questions"
        verbose_name = _("question")
        verbose_name_plural = _("questions")
        ordering  = ["order"]
        indexes   = [models.Index(fields=["quiz", "order"])]

    def __str__(self):
        return f"[{self.get_question_type_display()}] {self.text[:60]}"

    @property
    def is_auto_graded(self) -> bool:
        """Essay dan Code memerlukan manual grading."""
        return self.question_type not in (
            QuestionType.ESSAY, QuestionType.CODE
        )


class Answer(models.Model):
    """
    Pilihan jawaban untuk satu Question.
    Digunakan oleh tipe multiple_choice dan true_false.
    """
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question   = models.ForeignKey(
                   Question,
                   on_delete=models.CASCADE,
                   related_name="answers",
                 )
    text       = models.CharField(_("answer text"), max_length=500)
    is_correct = models.BooleanField(_("is correct"), default=False)
    order      = models.PositiveSmallIntegerField(_("order"), default=0)
    feedback   = models.TextField(
                   _("per-answer feedback"), blank=True,
                   help_text=_("Feedback khusus jika jawaban ini dipilih"),
                 )

    class Meta:
        db_table  = "quiz_answers"
        verbose_name = _("answer")
        verbose_name_plural = _("answers")
        ordering  = ["order"]

    def __str__(self):
        mark = "✓" if self.is_correct else "✗"
        return f"{mark} {self.text[:60]}"
    
# tambahkan di bagian bawah apps/quizzes/models.py

# class EssayGrading(models.Model):
#     id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     answer_record = models.OneToOneField(
#                       "enrollments.QuizAnswerRecord",
#                       on_delete=models.CASCADE,
#                       related_name="essay_grading",
#                     )
#     graded_by     = models.ForeignKey(
#                       settings.AUTH_USER_MODEL,
#                       on_delete=models.SET_NULL,
#                       null=True,
#                       related_name="essay_gradings",
#                       limit_choices_to={"role__in": ["instructor", "staff", "admin"]},
#                     )
#     score         = models.FloatField(
#                       _("score"), default=0.0,
#                       validators=[MinValueValidator(0.0)],
#                     )
#     feedback      = models.TextField(_("grader feedback"), blank=True)
#     graded_at     = models.DateTimeField(_("graded at"), default=timezone.now)

#     class Meta:
#         db_table     = "essay_gradings"
#         verbose_name = _("essay grading")
#         verbose_name_plural = _("essay gradings")
#         ordering     = ["-graded_at"]

#     def __str__(self):
#         return f"Grading by {self.graded_by} | Score: {self.score}"