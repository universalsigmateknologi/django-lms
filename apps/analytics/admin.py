from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import CourseAnalytic, InstructorAnalytic, PlatformAnalytic, UserActivityLog


@admin.register(CourseAnalytic)
class CourseAnalyticAdmin(admin.ModelAdmin):
    list_display    = (
        "course_title", "date",
        "total_enrollments", "new_enrollments",
        "total_completions", "completion_rate_display",
        "drop_rate_display", "avg_progress_display",
        "total_revenue", "avg_rating",
    )
    list_filter     = ("date",)
    search_fields   = ("course__title", "course__instructor__email")
    ordering        = ("-date",)
    readonly_fields = tuple(
        f.name for f in CourseAnalytic._meta.get_fields()
        if hasattr(f, "name")
    )
    date_hierarchy  = "date"

    # Tidak ada yang bisa diedit — pure read-only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="Course", ordering="course__title")
    def course_title(self, obj):
        return obj.course.title

    @admin.display(description="Completion Rate")
    def completion_rate_display(self, obj):
        pct   = round(obj.completion_rate, 1)
        color = "#1D9E75" if pct >= 70 else "#BA7517" if pct >= 40 else "#C0392B"
        return format_html(
            '<span style="color:{color};font-weight:500;">{pct}%</span>',
            color=color, pct=pct,
        )

    @admin.display(description="Drop Rate")
    def drop_rate_display(self, obj):
        pct   = round(obj.drop_rate, 1)
        color = "#C0392B" if pct >= 30 else "#BA7517" if pct >= 15 else "#1D9E75"
        return format_html(
            '<span style="color:{color};font-weight:500;">{pct}%</span>',
            color=color, pct=pct,
        )

    @admin.display(description="Avg Progress")
    def avg_progress_display(self, obj):
        pct = round(obj.avg_progress_pct, 1)
        return format_html(
            '<div style="width:80px;background:#eee;border-radius:4px;">'
            '<div style="width:{pct}%;background:#378ADD;border-radius:4px;'
            'text-align:center;color:#fff;font-size:11px;min-width:28px;">'
            '{pct}%</div></div>',
            pct=int(pct),
        )

    # Action — generate snapshot real-time
    actions = ["generate_snapshot"]

    @admin.action(description="Generate snapshot hari ini")
    def generate_snapshot(self, request, queryset):
        from .services import CourseAnalyticService
        from django.utils import timezone
        updated = 0
        for analytic in queryset:
            data = CourseAnalyticService.snapshot(analytic.course)
            for field, value in data.items():
                setattr(analytic, field, value)
            analytic.save()
            updated += 1
        self.message_user(request, f"{updated} snapshot berhasil diperbarui.")


@admin.register(InstructorAnalytic)
class InstructorAnalyticAdmin(admin.ModelAdmin):
    list_display    = (
        "instructor_email", "date",
        "total_courses", "published_courses",
        "total_students", "new_students",
        "total_revenue", "new_revenue",
        "avg_rating", "total_completions",
    )
    list_filter     = ("date",)
    search_fields   = ("instructor__email", "instructor__username")
    ordering        = ("-date",)
    readonly_fields = tuple(
        f.name for f in InstructorAnalytic._meta.get_fields()
        if hasattr(f, "name")
    )
    date_hierarchy  = "date"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="Instructor", ordering="instructor__email")
    def instructor_email(self, obj):
        return obj.instructor.email


@admin.register(PlatformAnalytic)
class PlatformAnalyticAdmin(admin.ModelAdmin):
    list_display    = (
        "date",
        "total_users", "new_users", "active_users",
        "total_courses", "published_courses",
        "total_enrollments", "new_enrollments",
        "total_completions", "total_revenue", "new_revenue",
        "quiz_pass_rate_display", "total_certificates",
    )
    list_filter     = ("date",)
    ordering        = ("-date",)
    readonly_fields = tuple(
        f.name for f in PlatformAnalytic._meta.get_fields()
        if hasattr(f, "name")
    )
    date_hierarchy  = "date"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="Quiz Pass Rate")
    def quiz_pass_rate_display(self, obj):
        pct   = round(obj.quiz_pass_rate, 1)
        color = "#1D9E75" if pct >= 70 else "#BA7517" if pct >= 50 else "#C0392B"
        return format_html(
            '<span style="color:{color};font-weight:500;">{pct}%</span>',
            color=color, pct=pct,
        )

    actions = ["generate_platform_snapshot"]

    @admin.action(description="Generate platform snapshot hari ini")
    def generate_platform_snapshot(self, request, queryset):
        from .services import PlatformAnalyticService
        from django.utils import timezone
        data    = PlatformAnalyticService.snapshot()
        today   = timezone.now().date()
        analytic, _ = PlatformAnalytic.objects.get_or_create(date=today)
        for field, value in data.items():
            setattr(analytic, field, value)
        analytic.save()
        self.message_user(request, "Platform snapshot hari ini berhasil diperbarui.")


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display    = (
        "user_email", "activity_type",
        "course_title", "lesson_title",
        "ip_address", "created_at",
    )
    list_filter     = ("activity_type", "created_at")
    search_fields   = (
        "user__email", "user__username",
        "course__title", "lesson__title",
        "ip_address",
    )
    ordering        = ("-created_at",)
    readonly_fields = (
        "id", "user", "activity_type",
        "course", "lesson", "metadata",
        "ip_address", "user_agent", "created_at",
    )
    date_hierarchy  = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Course")
    def course_title(self, obj):
        return obj.course.title if obj.course else "—"

    @admin.display(description="Lesson")
    def lesson_title(self, obj):
        return obj.lesson.title if obj.lesson else "—"