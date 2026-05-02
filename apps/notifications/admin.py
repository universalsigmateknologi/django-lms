from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Notification, EmailNotification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = (
        "title", "recipient_email", "actor_email",
        "notification_type", "is_read_badge",
        "created_at", "read_at",
    )
    list_filter     = ("notification_type", "is_read", "created_at")
    search_fields   = (
        "title", "message",
        "recipient__email", "actor__email",
    )
    ordering        = ("-created_at",)
    readonly_fields = ("id", "created_at", "read_at")

    fieldsets = (
        (_("Penerima"), {
            "fields": ("id", "recipient", "actor"),
        }),
        (_("Konten"), {
            "fields": ("notification_type", "title", "message", "action_url"),
        }),
        (_("Status"), {
            "fields": ("is_read", "read_at"),
        }),
        (_("Timestamp"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Recipient", ordering="recipient__email")
    def recipient_email(self, obj):
        return obj.recipient.email

    @admin.display(description="Actor")
    def actor_email(self, obj):
        return obj.actor.email if obj.actor else "—"

    @admin.display(description="Read?")
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span style="background:#E8F5E9;color:#1D9E75;padding:3px 10px;'
                'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
                _("Read")
            )
        return format_html(
            '<span style="background:#EAF3FB;color:#378ADD;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
            _("Unread")
        )

    actions = ["mark_all_read", "mark_all_unread"]

    @admin.action(description="Tandai sebagai sudah dibaca")
    def mark_all_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"{queryset.count()} notifikasi ditandai sudah dibaca.")

    @admin.action(description="Tandai sebagai belum dibaca")
    def mark_all_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"{queryset.count()} notifikasi ditandai belum dibaca.")


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display    = (
        "subject", "recipient_email",
        "status_badge", "retry_count",
        "can_retry_display", "scheduled_at", "sent_at",
    )
    list_filter     = ("status", "scheduled_at")
    search_fields   = ("subject", "recipient__email")
    ordering        = ("-created_at",)
    readonly_fields = (
        "id", "retry_count", "error_log",
        "sent_at", "created_at",
    )

    fieldsets = (
        (_("Penerima"), {
            "fields": ("id", "recipient", "notification"),
        }),
        (_("Konten Email"), {
            "fields": ("subject", "body_html", "body_text"),
        }),
        (_("Status Pengiriman"), {
            "fields": (
                "status", "retry_count", "max_retries",
                "scheduled_at", "sent_at",
            ),
        }),
        (_("Error Log"), {
            "fields": ("error_log",),
            "classes": ("collapse",),
        }),
        (_("Timestamp"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Recipient", ordering="recipient__email")
    def recipient_email(self, obj):
        return obj.recipient.email

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending":   ("#BA7517", "#FFF8E1"),
            "sent":      ("#1D9E75", "#E8F5E9"),
            "failed":    ("#C0392B", "#FDEDEC"),
            "cancelled": ("#7F8C8D", "#F2F3F4"),
        }
        color, bg = colors.get(obj.status, ("#555", "#eee"))
        return format_html(
            '<span style="background:{bg};color:{color};padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:500;">{label}</span>',
            bg=bg, color=color,
            label=obj.get_status_display(),
        )

    @admin.display(description="Can Retry?", boolean=True)
    def can_retry_display(self, obj):
        return obj.can_retry

    actions = ["retry_failed_emails", "cancel_pending_emails"]
    
    # nanti kalau sudah siap implementasi task untuk retry email, uncomment method ini

    # @admin.action(description="Retry email yang gagal")
    # def retry_failed_emails(self, request, queryset):
    #     from apps.notifications.tasks import send_email_notification
    #     retried = 0
    #     for email in queryset.filter(status="failed"):
    #         if email.can_retry:
    #             send_email_notification.delay(str(email.id))
    #             retried += 1
    #     self.message_user(request, f"{retried} email dijadwalkan ulang.")
    
    # untuk saat ini pakai ini dulu
    @admin.action(description="Retry email yang gagal")
    def retry_failed_emails(self, request, queryset):
        retried = 0
        for email in queryset.filter(status="failed"):
            if email.can_retry:
                email.status = EmailNotification.EmailStatus.PENDING
                email.retry_count += 1
                email.save(update_fields=["status", "retry_count"])
                retried += 1
        self.message_user(request, f"{retried} email direset ke pending.")

    @admin.action(description="Batalkan email pending")
    def cancel_pending_emails(self, request, queryset):
        updated = queryset.filter(status="pending").update(
            status=EmailNotification.EmailStatus.CANCELLED
        )
        self.message_user(request, f"{updated} email dibatalkan.")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display    = (
        "user_email", "in_app_enabled", "email_enabled",
        "email_enrollment", "email_quiz",
        "email_discussion", "email_payment",
        "email_certificate", "weekly_digest",
    )
    list_filter     = (
        "in_app_enabled", "email_enabled", "weekly_digest",
    )
    search_fields   = ("user__email", "user__username")
    ordering        = ("user__email",)
    readonly_fields = ("updated_at",)

    fieldsets = (
        (_("User"), {
            "fields": ("user",),
        }),
        (_("In-App"), {
            "fields": ("in_app_enabled",),
        }),
        (_("Email"), {
            "fields": (
                "email_enabled",
                "email_enrollment", "email_quiz",
                "email_discussion", "email_payment",
                "email_certificate",
            ),
        }),
        (_("Digest"), {
            "fields": ("weekly_digest",),
        }),
        (_("Timestamp"), {
            "fields": ("updated_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email