from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Certificate, CertificateTemplate


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display    = ("name", "is_default", "background_preview", "created_at")
    list_filter     = ("is_default",)
    search_fields   = ("name",)
    ordering        = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "background_preview")

    fieldsets = (
        (_("Informasi Template"), {
            "fields": ("id", "name", "is_default"),
        }),
        (_("Desain"), {
            "fields": ("background", "background_preview", "html_template"),
        }),
        (_("Timestamp"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Background Preview")
    def background_preview(self, obj):
        if obj.background:
            return format_html(
                '<img src="{}" style="height:60px;border-radius:4px;" />',
                obj.background.url,
            )
        return "-"


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display    = (
        "certificate_number", "student_name_snapshot",
        "course_title_snapshot", "instructor_name_snapshot",
        "is_valid_badge", "issued_at",
    )
    list_filter     = ("is_valid", "issued_at")
    search_fields   = (
        "certificate_number",
        "student_name_snapshot",
        "course_title_snapshot",
        "student__email",
    )
    ordering        = ("-issued_at",)
    readonly_fields = (
        "id", "certificate_number",
        "student_name_snapshot", "course_title_snapshot",
        "instructor_name_snapshot", "issued_at",
        "revoked_at", "pdf_preview",
    )

    fieldsets = (
        (_("Identitas Sertifikat"), {
            "fields": (
                "id", "certificate_number",
                "student", "course", "enrollment", "template",
            ),
        }),
        (_("Snapshot Data"), {
            "fields": (
                "student_name_snapshot",
                "course_title_snapshot",
                "instructor_name_snapshot",
            ),
        }),
        (_("File PDF"), {
            "fields": ("pdf_file", "pdf_preview"),
        }),
        (_("Status"), {
            "fields": ("is_valid", "revoked_at", "revoke_reason"),
        }),
        (_("Timestamp"), {
            "fields": ("issued_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Status")
    def is_valid_badge(self, obj):
        if obj.is_valid:
            return format_html(
                '<span style="background:#E8F5E9;color:#1D9E75;padding:3px 10px;'
                'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
                _("Valid")
            )
        return format_html(
            '<span style="background:#FDEDEC;color:#C0392B;padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:500;">{}</span>',
            _("Revoked")
        )

    @admin.display(description="PDF Preview")
    def pdf_preview(self, obj):
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank">'
                '<button style="padding:4px 12px;border-radius:4px;'
                'border:1px solid #ccc;cursor:pointer;">📄 Lihat PDF</button>'
                '</a>',
                obj.pdf_file.url,
            )
        return "-"

    actions = ["revoke_certificates", "revalidate_certificates"]

    @admin.action(description="Cabut sertifikat terpilih")
    def revoke_certificates(self, request, queryset):
        for cert in queryset:
            cert.revoke(reason="Dicabut oleh admin")
        self.message_user(request, f"{queryset.count()} sertifikat dicabut.")

    @admin.action(description="Aktifkan kembali sertifikat terpilih")
    def revalidate_certificates(self, request, queryset):
        queryset.update(is_valid=True, revoked_at=None, revoke_reason="")
        self.message_user(request, f"{queryset.count()} sertifikat diaktifkan kembali.")