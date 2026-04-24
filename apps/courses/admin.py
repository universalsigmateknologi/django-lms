from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Category, Tag, Course, Module, Lesson
from django.contrib.auth import get_user_model
User = get_user_model()


# ─── Inlines ─────────────────────────────────────────────────────────────────

class LessonInline(admin.TabularInline):
    model            = Lesson
    extra            = 0
    fields           = ("title", "lesson_type", "order", "is_free_preview", "duration_seconds")
    ordering         = ("order",)
    show_change_link = True


class ModuleInline(admin.StackedInline):
    model            = Module
    extra            = 0
    fields           = ("title", "order")
    ordering         = ("order",)
    show_change_link = True


# ─── ModelAdmin ──────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering      = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display  = ("name",)
    search_fields = ("name",)
    ordering      = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display  = (
        "title", "instructor_email", "category",
        "level", "price", "is_published",
        "created_at", "updated_at",
    )
    list_filter   = ("is_published", "level", "category")
    search_fields = ("title", "instructor__email", "instructor__username")
    ordering      = ("-created_at",)
    prepopulated_fields  = {"slug": ("title",)}
    filter_horizontal    = ("tags",)
    readonly_fields      = ("created_at", "updated_at", "thumbnail_preview")
    autocomplete_fields  = ("category",)
    inlines              = [ModuleInline]

    fieldsets = (
        (_("Informasi Kursus"), {
            "fields": (
                "instructor", "title", "slug",
                "category", "tags", "level",
            ),
        }),
        (_("Harga & Status"), {
            "fields": ("price", "is_published"),
        }),
        (_("Thumbnail"), {
            "fields": ("thumbnail", "thumbnail_preview"),
        }),
        (_("Timestamp"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Instructor", ordering="instructor__email")
    def instructor_email(self, obj):
        return obj.instructor.email

    @admin.display(description="Thumbnail Preview")
    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="height:80px;border-radius:6px;" />',
                obj.thumbnail.url,
            )
        return "-"

    actions = ["publish_courses", "unpublish_courses"]

    @admin.action(description="Publikasikan kursus terpilih")
    def publish_courses(self, request, queryset):
        updated = queryset.update(is_published=True)
        self.message_user(request, f"{updated} kursus dipublikasikan.")

    @admin.action(description="Sembunyikan kursus terpilih")
    def unpublish_courses(self, request, queryset):
        updated = queryset.update(is_published=False)
        self.message_user(request, f"{updated} kursus disembunyikan.")
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "instructor":
            kwargs["queryset"] = User.objects.filter(role="instructor")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display  = ("title", "course_title", "order", "created_at")
    list_filter   = ("course",)
    search_fields = ("title", "course__title")
    ordering      = ("course", "order")
    readonly_fields = ("created_at",)
    inlines       = [LessonInline]

    fieldsets = (
        (_("Informasi Modul"), {
            "fields": ("course", "title", "order"),
        }),
        (_("Timestamp"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Course", ordering="course__title")
    def course_title(self, obj):
        return obj.course.title


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display  = (
        "title", "module_title", "course_title",
        "lesson_type_badge", "order",
        "duration_fmt", "is_free_preview", "created_at",
    )
    list_filter   = ("lesson_type", "is_free_preview")
    search_fields = ("title", "module__title", "module__course__title")
    ordering      = ("module__course", "module__order", "order")
    readonly_fields = ("created_at",)

    fieldsets = (
        (_("Informasi Lesson"), {
            "fields": ("module", "title", "lesson_type", "order", "is_free_preview"),
        }),
        (_("Konten"), {
            "fields": ("video_url", "content", "duration_seconds"),
        }),
        (_("Timestamp"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Module", ordering="module__title")
    def module_title(self, obj):
        return obj.module.title

    @admin.display(description="Course", ordering="module__course__title")
    def course_title(self, obj):
        return obj.module.course.title

    @admin.display(description="Type")
    def lesson_type_badge(self, obj):
        colors = {
            "video": ("#1D9E75", "#E8F5E9"),
            "text":  ("#378ADD", "#EAF3FB"),
            "quiz":  ("#BA7517", "#FFF8E1"),
            "file":  ("#7F8C8D", "#F2F3F4"),
        }
        color, bg = colors.get(obj.lesson_type, ("#555", "#eee"))
        return format_html(
            '<span style="background:{bg};color:{color};padding:3px 10px;'
            'border-radius:12px;font-size:11px;font-weight:500;">{label}</span>',
            bg=bg, color=color,
            label=obj.get_lesson_type_display(),
        )

    @admin.display(description="Duration")
    def duration_fmt(self, obj):
        if obj.duration_seconds == 0:
            return "-"
        mins, secs = divmod(obj.duration_seconds, 60)
        return f"{mins:02d}:{secs:02d}"