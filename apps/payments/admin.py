from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import (
    Coupon, Order, OrderItem, Payment,
    Refund, InstructorRevenue,
    ManualPaymentProof, PaymentSettings, OrderStatus,
)


# ─── Inlines ─────────────────────────────────────────────────────────────────

class OrderItemInline(admin.TabularInline):
    model           = OrderItem
    extra           = 0
    readonly_fields = ("course", "course_title", "price_snapshot", "currency")
    can_delete      = False


class PaymentInline(admin.TabularInline):
    model           = Payment
    extra           = 0
    readonly_fields = ("gateway", "status", "transaction_id", "amount", "currency", "paid_at")
    can_delete      = False
    show_change_link = True


class ManualPaymentProofInline(admin.TabularInline):
    model           = ManualPaymentProof
    extra           = 0
    readonly_fields = ("proof_image_preview", "sender_name", "sender_bank", "notes", "uploaded_at")
    fields          = ("proof_image_preview", "sender_name", "sender_bank", "notes", "uploaded_at")
    can_delete      = False

    @admin.display(description="Bukti Transfer")
    def proof_image_preview(self, obj):
        if obj.proof_image:
            return format_html(
                '<a href="{url}" target="_blank">'
                '<img src="{url}" style="max-height:120px;border-radius:8px;'
                'border:1px solid #e2e8f0;" />'
                '</a>',
                url=obj.proof_image.url,
            )
        return "-"


# ─── ModelAdmin ──────────────────────────────────────────────────────────────

@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "admin_whatsapp", "payment_expiry_hours", "max_upload_size_mb")

    def has_add_permission(self, request):
        # Singleton: hanya boleh 1 record
        return not PaymentSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = (
        "code", "coupon_type", "discount_value",
        "used_count", "max_usage", "is_active",
        "valid_from", "valid_until", "is_valid_display",
    )
    list_filter   = ("coupon_type", "is_active")
    search_fields = ("code",)
    ordering      = ("-created_at",)
    readonly_fields = ("id", "used_count", "created_at")
    filter_horizontal = ("applicable_courses",)

    fieldsets = (
        (_("Informasi Kupon"), {
            "fields": ("id", "code", "coupon_type", "discount_value", "max_discount", "min_purchase"),
        }),
        (_("Batasan Penggunaan"), {
            "fields": ("max_usage", "used_count", "max_usage_per_user"),
        }),
        (_("Berlaku Untuk"), {
            "fields": ("applicable_courses",),
            "description": _("Kosongkan jika berlaku untuk semua kursus"),
        }),
        (_("Status & Masa Berlaku"), {
            "fields": ("is_active", "valid_from", "valid_until", "created_by", "created_at"),
        }),
    )

    @admin.display(description="Still Valid?", boolean=True)
    def is_valid_display(self, obj):
        return obj.is_valid

    actions = ["deactivate_coupons", "activate_coupons"]

    @admin.action(description="Nonaktifkan kupon terpilih")
    def deactivate_coupons(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} kupon dinonaktifkan.")

    @admin.action(description="Aktifkan kupon terpilih")
    def activate_coupons(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} kupon diaktifkan.")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = (
        "order_number", "user_email", "status_badge",
        "subtotal", "discount_amount", "total_amount",
        "currency", "created_at", "paid_at",
    )
    list_filter   = ("status", "currency", "created_at")
    search_fields = ("order_number", "user__email", "user__username")
    ordering      = ("-created_at",)
    readonly_fields = (
        "id", "order_number", "created_at",
        "updated_at", "paid_at",
    )
    inlines       = [OrderItemInline, PaymentInline, ManualPaymentProofInline]

    fieldsets = (
        (_("Identitas Order"), {
            "fields": ("id", "order_number", "user"),
        }),
        (_("Status & Pembayaran"), {
            "fields": ("status", "coupon", "notes"),
        }),
        (_("Nominal"), {
            "fields": ("currency", "subtotal", "discount_amount", "total_amount"),
        }),
        (_("Timestamp"), {
            "fields": ("created_at", "updated_at", "paid_at", "expired_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "pending":              ("#BA7517", "#FFF8E1"),
            "waiting_verification": ("#1565C0", "#E3F2FD"),
            "paid":                 ("#1D9E75", "#E8F5E9"),
            "failed":               ("#C0392B", "#FDEDEC"),
            "cancelled":            ("#7F8C8D", "#F2F3F4"),
            "refunded":             ("#8E44AD", "#F5EEF8"),
            "expired":              ("#555",    "#eee"),
        }
        color, bg = colors.get(obj.status, ("#555", "#eee"))
        return format_html(
            '<span style="background:{bg};color:{color};padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:500;">{label}</span>',
            bg=bg, color=color,
            label=obj.get_status_display(),
        )

    actions = ["mark_paid", "mark_cancelled", "mark_refunded"]

    @admin.action(description="✅ Tandai sebagai Paid (auto-enroll)")
    def mark_paid(self, request, queryset):
        for order in queryset:
            order.mark_paid()
        self.message_user(request, f"{queryset.count()} order ditandai paid & enrollment dibuat otomatis.")

    @admin.action(description="❌ Tandai sebagai Cancelled")
    def mark_cancelled(self, request, queryset):
        for order in queryset:
            order.mark_cancelled()
        self.message_user(request, f"{queryset.count()} order dibatalkan.")

    @admin.action(description="↩️ Tandai sebagai Refunded")
    def mark_refunded(self, request, queryset):
        for order in queryset:
            order.mark_refunded()
        self.message_user(request, f"{queryset.count()} order direfund.")


@admin.register(ManualPaymentProof)
class ManualPaymentProofAdmin(admin.ModelAdmin):
    list_display  = (
        "order_number", "sender_name", "sender_bank",
        "proof_preview_small", "uploaded_at", "is_reviewed",
    )
    list_filter   = ("sender_bank", "uploaded_at")
    search_fields = ("order__order_number", "sender_name")
    ordering      = ("-uploaded_at",)
    readonly_fields = (
        "id", "uploaded_at", "proof_image_preview",
    )

    fieldsets = (
        (_("Informasi Bukti"), {
            "fields": ("id", "order", "proof_image_preview", "proof_image"),
        }),
        (_("Detail Pengirim"), {
            "fields": ("sender_name", "sender_bank", "notes"),
        }),
        (_("Review"), {
            "fields": ("reviewed_by", "reviewed_at", "admin_note"),
        }),
    )

    @admin.display(description="Order")
    def order_number(self, obj):
        return obj.order.order_number

    @admin.display(description="Preview")
    def proof_preview_small(self, obj):
        if obj.proof_image:
            return format_html(
                '<img src="{}" style="max-height:40px;border-radius:4px;" />',
                obj.proof_image.url,
            )
        return "-"

    @admin.display(description="Bukti Transfer (Full)")
    def proof_image_preview(self, obj):
        if obj.proof_image:
            return format_html(
                '<a href="{url}" target="_blank">'
                '<img src="{url}" style="max-height:300px;border-radius:12px;'
                'border:1px solid #e2e8f0;" />'
                '</a>',
                url=obj.proof_image.url,
            )
        return "-"

    @admin.display(description="Reviewed?", boolean=True)
    def is_reviewed(self, obj):
        return obj.reviewed_at is not None

    actions = ["approve_and_mark_paid", "reject_proof"]

    @admin.action(description="✅ Approve & Mark Order as Paid")
    def approve_and_mark_paid(self, request, queryset):
        for proof in queryset:
            proof.reviewed_by = request.user
            proof.reviewed_at = timezone.now()
            proof.save(update_fields=["reviewed_by", "reviewed_at"])
            proof.order.mark_paid()
        self.message_user(
            request,
            f"{queryset.count()} bukti diapprove & order ditandai paid."
        )

    @admin.action(description="❌ Reject & Cancel Order")
    def reject_proof(self, request, queryset):
        for proof in queryset:
            proof.reviewed_by = request.user
            proof.reviewed_at = timezone.now()
            proof.admin_note = "Ditolak oleh admin"
            proof.save(update_fields=["reviewed_by", "reviewed_at", "admin_note"])
            proof.order.mark_cancelled()
        self.message_user(
            request,
            f"{queryset.count()} bukti ditolak & order dibatalkan."
        )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = (
        "transaction_id", "order_number", "gateway",
        "status", "amount", "currency",
        "payment_method", "paid_at", "created_at",
    )
    list_filter   = ("gateway", "status", "currency")
    search_fields = ("transaction_id", "order__order_number", "order__user__email")
    ordering      = ("-created_at",)
    readonly_fields = (
        "id", "transaction_id", "gateway_response",
        "created_at", "updated_at", "paid_at",
    )

    fieldsets = (
        (_("Identitas"), {
            "fields": ("id", "order", "gateway", "transaction_id"),
        }),
        (_("Detail Pembayaran"), {
            "fields": ("status", "amount", "currency", "payment_method"),
        }),
        (_("Response Gateway"), {
            "fields": ("gateway_response",),
            "classes": ("collapse",),
        }),
        (_("Timestamp"), {
            "fields": ("paid_at", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Order Number")
    def order_number(self, obj):
        return obj.order.order_number


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display  = (
        "payment_txn", "requested_by_email", "status",
        "refund_amount", "reviewed_by_email",
        "requested_at", "processed_at",
    )
    list_filter   = ("status", "requested_at")
    search_fields = (
        "payment__transaction_id",
        "requested_by__email",
        "reviewed_by__email",
    )
    ordering      = ("-requested_at",)
    readonly_fields = ("id", "requested_at", "processed_at")

    fieldsets = (
        (_("Referensi"), {
            "fields": ("id", "payment", "requested_by"),
        }),
        (_("Detail Refund"), {
            "fields": ("status", "reason", "refund_amount"),
        }),
        (_("Review Admin"), {
            "fields": ("reviewed_by", "admin_note"),
        }),
        (_("Timestamp"), {
            "fields": ("requested_at", "processed_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Transaction ID")
    def payment_txn(self, obj):
        return obj.payment.transaction_id

    @admin.display(description="Requested By")
    def requested_by_email(self, obj):
        return obj.requested_by.email if obj.requested_by else "-"

    @admin.display(description="Reviewed By")
    def reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by else "-"

    actions = ["approve_refund", "reject_refund"]

    @admin.action(description="Approve refund terpilih")
    def approve_refund(self, request, queryset):
        queryset.update(
            status=Refund.RefundStatus.APPROVED,
            reviewed_by=request.user,
        )
        self.message_user(request, f"{queryset.count()} refund diapprove.")

    @admin.action(description="Reject refund terpilih")
    def reject_refund(self, request, queryset):
        queryset.update(
            status=Refund.RefundStatus.REJECTED,
            reviewed_by=request.user,
        )
        self.message_user(request, f"{queryset.count()} refund ditolak.")


@admin.register(InstructorRevenue)
class InstructorRevenueAdmin(admin.ModelAdmin):
    list_display  = (
        "instructor_email", "course_title",
        "gross_amount", "revenue_pct", "net_amount",
        "is_paid_out", "paid_out_at", "created_at",
    )
    list_filter   = ("is_paid_out",)
    search_fields = ("instructor__email", "order_item__course_title")
    ordering      = ("-created_at",)
    readonly_fields = ("id", "gross_amount", "net_amount", "created_at")

    fieldsets = (
        (_("Relasi"), {
            "fields": ("id", "instructor", "order_item"),
        }),
        (_("Revenue"), {
            "fields": ("revenue_pct", "gross_amount", "net_amount"),
        }),
        (_("Payout"), {
            "fields": ("is_paid_out", "paid_out_at"),
        }),
    )

    @admin.display(description="Instructor", ordering="instructor__email")
    def instructor_email(self, obj):
        return obj.instructor.email

    @admin.display(description="Course")
    def course_title(self, obj):
        return obj.order_item.course_title

    actions = ["mark_paid_out"]

    @admin.action(description="Tandai sudah dibayarkan ke instruktur")
    def mark_paid_out(self, request, queryset):
        queryset.update(is_paid_out=True, paid_out_at=timezone.now())
        self.message_user(request, f"{queryset.count()} revenue ditandai paid out.")