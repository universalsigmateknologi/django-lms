import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Discussion(models.Model):
    """
    Thread diskusi / pertanyaan yang dibuat oleh student atau instruktur
    pada sebuah lesson tertentu.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lesson      = models.ForeignKey(
                    "courses.Lesson",
                    on_delete=models.CASCADE,
                    related_name="discussions",
                  )
    author      = models.ForeignKey(
                    settings.AUTH_USER_MODEL,
                    on_delete=models.CASCADE,
                    related_name="discussions",
                  )
    title       = models.CharField(_("title"), max_length=255)
    body        = models.TextField(_("body"))
    is_pinned   = models.BooleanField(_("is pinned"), default=False)
    is_closed   = models.BooleanField(
                    _("is closed"), default=False,
                    help_text=_("Jika ditutup, tidak bisa ada reply baru"),
                  )
    is_answered = models.BooleanField(_("is answered"), default=False)
    upvotes     = models.ManyToManyField(
                    settings.AUTH_USER_MODEL,
                    blank=True,
                    related_name="upvoted_discussions",
                    verbose_name=_("upvotes"),
                  )
    # Flag moderasi
    is_flagged  = models.BooleanField(_("is flagged"), default=False)
    flag_reason = models.TextField(_("flag reason"), blank=True)
    created_at  = models.DateTimeField(_("created at"), default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = "discussions"
        verbose_name = _("discussion")
        verbose_name_plural = _("discussions")
        ordering     = ["-is_pinned", "-created_at"]
        indexes      = [
            models.Index(fields=["lesson", "is_pinned"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["is_flagged"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.author.email}"

    @property
    def upvote_count(self) -> int:
        return self.upvotes.count()

    @property
    def reply_count(self) -> int:
        return self.replies.count()

    def close(self):
        self.is_closed = True
        self.save(update_fields=["is_closed"])

    def pin(self):
        self.is_pinned = True
        self.save(update_fields=["is_pinned"])

    def mark_answered(self):
        self.is_answered = True
        self.save(update_fields=["is_answered"])


class Reply(models.Model):
    """
    Balasan pada sebuah Discussion.
    Mendukung nested reply (satu level) via parent FK.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discussion  = models.ForeignKey(
                    Discussion,
                    on_delete=models.CASCADE,
                    related_name="replies",
                  )
    author      = models.ForeignKey(
                    settings.AUTH_USER_MODEL,
                    on_delete=models.CASCADE,
                    related_name="replies",
                  )
    # Nested reply — null berarti reply langsung ke discussion
    parent      = models.ForeignKey(
                    "self",
                    on_delete=models.CASCADE,
                    null=True, blank=True,
                    related_name="children",
                  )
    body        = models.TextField(_("body"))
    is_accepted = models.BooleanField(
                    _("is accepted answer"), default=False,
                    help_text=_("Ditandai oleh author discussion atau instruktur sebagai jawaban terbaik"),
                  )
    upvotes     = models.ManyToManyField(
                    settings.AUTH_USER_MODEL,
                    blank=True,
                    related_name="upvoted_replies",
                    verbose_name=_("upvotes"),
                  )
    # Flag moderasi
    is_flagged  = models.BooleanField(_("is flagged"), default=False)
    flag_reason = models.TextField(_("flag reason"), blank=True)
    created_at  = models.DateTimeField(_("created at"), default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = "discussion_replies"
        verbose_name = _("reply")
        verbose_name_plural = _("replies")
        ordering     = ["-is_accepted", "created_at"]
        indexes      = [
            models.Index(fields=["discussion", "is_accepted"]),
            models.Index(fields=["author", "created_at"]),
            models.Index(fields=["is_flagged"]),
        ]

    def __str__(self):
        return f"Reply by {self.author.email} on [{self.discussion.title[:40]}]"

    @property
    def upvote_count(self) -> int:
        return self.upvotes.count()

    @property
    def is_root_reply(self) -> bool:
        """True jika reply langsung ke discussion, bukan ke reply lain."""
        return self.parent is None

    def accept(self):
        """
        Tandai sebagai jawaban terbaik.
        Otomatis mark discussion sebagai answered.
        """
        # Batalkan accepted reply sebelumnya di discussion yang sama
        Reply.objects.filter(
            discussion=self.discussion,
            is_accepted=True,
        ).exclude(pk=self.pk).update(is_accepted=False)

        self.is_accepted = True
        self.save(update_fields=["is_accepted"])
        self.discussion.mark_answered()


class DiscussionFlag(models.Model):
    """
    Detail laporan flag dari user terhadap Discussion atau Reply.
    """
    class FlagReason(models.TextChoices):
        SPAM        = "spam",        _("Spam")
        HARASSMENT  = "harassment",  _("Harassment")
        IRRELEVANT  = "irrelevant",  _("Irrelevant")
        OFFENSIVE   = "offensive",   _("Offensive")
        OTHER       = "other",       _("Other")

    class ContentType(models.TextChoices):
        DISCUSSION = "discussion", _("Discussion")
        REPLY      = "reply",      _("Reply")

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reported_by  = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.CASCADE,
                     related_name="flags_reported",
                   )
    content_type = models.CharField(
                     _("content type"), max_length=20,
                     choices=ContentType.choices,
                   )
    # Salah satu dari dua FK ini diisi, yang lain null
    discussion   = models.ForeignKey(
                     Discussion,
                     on_delete=models.CASCADE,
                     null=True, blank=True,
                     related_name="flags",
                   )
    reply        = models.ForeignKey(
                     Reply,
                     on_delete=models.CASCADE,
                     null=True, blank=True,
                     related_name="flags",
                   )
    reason       = models.CharField(
                     _("reason"), max_length=20,
                     choices=FlagReason.choices,
                     default=FlagReason.OTHER,
                   )
    description  = models.TextField(_("description"), blank=True)
    is_resolved  = models.BooleanField(_("is resolved"), default=False)
    resolved_by  = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.SET_NULL,
                     null=True, blank=True,
                     related_name="flags_resolved",
                   )
    created_at   = models.DateTimeField(auto_now_add=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table     = "discussion_flags"
        verbose_name = _("discussion flag")
        verbose_name_plural = _("discussion flags")
        ordering     = ["-created_at"]
        indexes      = [
            models.Index(fields=["is_resolved", "created_at"]),
        ]

    def __str__(self):
        return f"Flag by {self.reported_by.email} | {self.content_type} | {self.reason}"

    def resolve(self, resolved_by):
        self.is_resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.save(update_fields=["is_resolved", "resolved_by", "resolved_at"])