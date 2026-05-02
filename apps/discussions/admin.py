from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Discussion, Reply, DiscussionFlag


# ─── Inlines ─────────────────────────────────────────────────────────────────

class ReplyInline(admin.TabularInline):
    model            = Reply
    extra            = 0
    fields           = ("author", "body", "is_accepted", "is_flagged", "created_at")
    readonly_fields  = ("created_at",)
    show_change_link = True
    ordering         = ("created_at",)


class DiscussionFlagInline(admin.TabularInline):
    model           = DiscussionFlag
    extra           = 0
    fields          = ("reported_by", "reason", "description", "is_resolved", "created_at")
    readonly_fields = ("reported_by", "reason", "description", "created_at")
    can_delete      = False
    show_change_link = True


# ─── ModelAdmin ──────────────────────────────────────────────────────────────

@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display    = (
        "title", "author_email", "lesson_title",
        "course_title", "reply_count_display",
        "upvote_count_display", "is_pinned",
        "is_answered", "is_closed",
        "is_flagged_badge", "created_at",
    )
    list_filter     = ("is_pinned", "is_answered", "is_closed", "is_flagged")
    search_fields   = (
        "title", "body",
        "author__email", "author__username",
        "lesson__title", "lesson__module__course__title",
    )
    ordering        = ("-is_pinned", "-created_at")
    readonly_fields = ("id", "upvote_count_display", "reply_count_display", "created_at", "updated_at")
    filter_horizontal = ("upvotes",)
    inlines         = [ReplyInline, DiscussionFlagInline]

    fieldsets = (
        (_("Konten"), {
            "fields": ("id", "lesson", "author", "title", "body"),
        }),
        (_("Status"), {
            "fields": ("is_pinned", "is_closed", "is_answered"),
        }),
        (_("Moderasi"), {
            "fields": ("is_flagged", "flag_reason"),
            "classes": ("collapse",),
        }),
        (_("Statistik"), {
            "fields": ("upvote_count_display", "reply_count_display"),
            "classes": ("collapse",),
        }),
        (_("Timestamp"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Author", ordering="author__email")
    def author_email(self, obj):
        return obj.author.email

    @admin.display(description="Lesson", ordering="lesson__title")
    def lesson_title(self, obj):
        return obj.lesson.title

    @admin.display(description="Course")
    def course_title(self, obj):
        return obj.lesson.module.course.title

    @admin.display(description="Replies")
    def reply_count_display(self, obj):
        return obj.reply_count

    @admin.display(description="Upvotes")
    def upvote_count_display(self, obj):
        return obj.upvote_count

    @admin.display(description="Flagged?")
    def is_flagged_badge(self, obj):
        if obj.is_flagged:
            return format_html(
                '<span style="background:#FDEDEC;color:#C0392B;padding:3px 10px;'
                'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
                "⚑ Flagged"
            )
        return format_html('<span style="color:#aaa;font-size:11px;">{}</span>', "—")

    actions = [
        "pin_discussions", "unpin_discussions",
        "close_discussions", "open_discussions",
        "clear_flags",
    ]

    @admin.action(description="Pin diskusi terpilih")
    def pin_discussions(self, request, queryset):
        queryset.update(is_pinned=True)
        self.message_user(request, f"{queryset.count()} diskusi di-pin.")

    @admin.action(description="Unpin diskusi terpilih")
    def unpin_discussions(self, request, queryset):
        queryset.update(is_pinned=False)
        self.message_user(request, f"{queryset.count()} diskusi di-unpin.")

    @admin.action(description="Tutup diskusi terpilih")
    def close_discussions(self, request, queryset):
        queryset.update(is_closed=True)
        self.message_user(request, f"{queryset.count()} diskusi ditutup.")

    @admin.action(description="Buka kembali diskusi terpilih")
    def open_discussions(self, request, queryset):
        queryset.update(is_closed=False)
        self.message_user(request, f"{queryset.count()} diskusi dibuka kembali.")

    @admin.action(description="Hapus flag diskusi terpilih")
    def clear_flags(self, request, queryset):
        queryset.update(is_flagged=False, flag_reason="")
        self.message_user(request, f"{queryset.count()} flag dihapus.")


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display    = (
        "short_body", "author_email",
        "discussion_title", "parent_reply",
        "is_accepted", "upvote_count_display",
        "is_flagged_badge", "created_at",
    )
    list_filter     = ("is_accepted", "is_flagged")
    search_fields   = (
        "body", "author__email",
        "discussion__title",
    )
    ordering        = ("-created_at",)
    readonly_fields = ("id", "upvote_count_display", "created_at", "updated_at")
    filter_horizontal = ("upvotes",)

    fieldsets = (
        (_("Konten"), {
            "fields": ("id", "discussion", "parent", "author", "body"),
        }),
        (_("Status"), {
            "fields": ("is_accepted",),
        }),
        (_("Moderasi"), {
            "fields": ("is_flagged", "flag_reason"),
            "classes": ("collapse",),
        }),
        (_("Statistik"), {
            "fields": ("upvote_count_display",),
            "classes": ("collapse",),
        }),
        (_("Timestamp"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Body")
    def short_body(self, obj):
        return obj.body[:60] + "..." if len(obj.body) > 60 else obj.body

    @admin.display(description="Author", ordering="author__email")
    def author_email(self, obj):
        return obj.author.email

    @admin.display(description="Discussion", ordering="discussion__title")
    def discussion_title(self, obj):
        return obj.discussion.title[:50]

    @admin.display(description="Parent Reply")
    def parent_reply(self, obj):
        if obj.parent:
            return obj.parent.body[:40] + "..."
        return "—"

    @admin.display(description="Upvotes")
    def upvote_count_display(self, obj):
        return obj.upvote_count

    @admin.display(description="Flagged?")
    def is_flagged_badge(self, obj):
        if obj.is_flagged:
            return format_html(
                '<span style="background:#FDEDEC;color:#C0392B;padding:3px 10px;'
                'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
                "⚑ Flagged"
            )
        return format_html('<span style="color:#aaa;font-size:11px;">{}</span>', "—")

    actions = ["accept_replies", "clear_flags"]

    @admin.action(description="Tandai sebagai jawaban terbaik")
    def accept_replies(self, request, queryset):
        for reply in queryset:
            reply.accept()
        self.message_user(request, f"{queryset.count()} reply ditandai sebagai jawaban terbaik.")

    @admin.action(description="Hapus flag reply terpilih")
    def clear_flags(self, request, queryset):
        queryset.update(is_flagged=False, flag_reason="")
        self.message_user(request, f"{queryset.count()} flag dihapus.")


@admin.register(DiscussionFlag)
class DiscussionFlagAdmin(admin.ModelAdmin):
    list_display    = (
        "reported_by_email", "content_type",
        "flagged_content", "reason",
        "is_resolved_badge", "resolved_by_email",
        "created_at",
    )
    list_filter     = ("content_type", "reason", "is_resolved")
    search_fields   = (
        "reported_by__email",
        "discussion__title",
        "reply__body",
    )
    ordering        = ("is_resolved", "-created_at")
    readonly_fields = (
        "id", "reported_by", "content_type",
        "discussion", "reply", "reason",
        "description", "created_at", "resolved_at",
    )

    fieldsets = (
        (_("Laporan"), {
            "fields": (
                "id", "reported_by", "content_type",
                "discussion", "reply",
                "reason", "description",
            ),
        }),
        (_("Resolusi"), {
            "fields": ("is_resolved", "resolved_by", "resolved_at"),
        }),
        (_("Timestamp"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Reported By", ordering="reported_by__email")
    def reported_by_email(self, obj):
        return obj.reported_by.email

    @admin.display(description="Konten")
    def flagged_content(self, obj):
        if obj.content_type == DiscussionFlag.ContentType.DISCUSSION and obj.discussion:
            return f"[Discussion] {obj.discussion.title[:40]}"
        if obj.content_type == DiscussionFlag.ContentType.REPLY and obj.reply:
            return f"[Reply] {obj.reply.body[:40]}"
        return "-"

    @admin.display(description="Resolved?")
    def is_resolved_badge(self, obj):
        if obj.is_resolved:
            return format_html(
                '<span style="background:#E8F5E9;color:#1D9E75;padding:3px 10px;'
                'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
                _("Resolved")
            )
        return format_html(
            '<span style="background:#FDEDEC;color:#C0392B;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
            _("Pending")
        )

    @admin.display(description="Resolved By")
    def resolved_by_email(self, obj):
        return obj.resolved_by.email if obj.resolved_by else "—"

    actions = ["resolve_flags"]

    @admin.action(description="Tandai flag terpilih sebagai resolved")
    def resolve_flags(self, request, queryset):
        for flag in queryset:
            flag.resolve(resolved_by=request.user)
        self.message_user(request, f"{queryset.count()} flag ditandai resolved.")