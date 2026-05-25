from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

User = get_user_model()


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Course(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Verification'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    ]

    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='courses')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    thumbnail = models.ImageField(upload_to='course_thumbnails/')
    is_lesson_finished = models.BooleanField(default=False)
    is_online = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def student_count(self):
        return self.enrollments.count()

    @property
    def total_duration_hours(self):
        from django.db.models import Sum
        total_seconds = self.modules.aggregate(
            total=Sum('lessons__duration_seconds')
        )['total'] or 0
        return round(total_seconds / 3600, 1)

    @property
    def first_lesson(self):
        """Returns the first lesson of the course based on module and lesson order."""
        return Lesson.objects.filter(module__course=self).order_by('module__order', 'order').first()

    def __str__(self):
        return self.title


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['course', 'order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    LESSON_TYPE_CHOICES = [
        ('video', 'Video'),
        ('text', 'Text'),
        ('quiz', 'Quiz'),
        ('file', 'File'),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=10, choices=LESSON_TYPE_CHOICES)
    video_url = models.URLField(blank=True, null=True)
    content = CKEditor5Field('Content', config_name='extends')# bisa diganti RichTextField kalau pakai ckeditor
    file = models.FileField(upload_to='lesson_files/', blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    is_free_preview = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = ['module', 'order']

    def __str__(self):
        return f"{self.module.title} - {self.title}"