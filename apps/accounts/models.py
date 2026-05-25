from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email wajib diisi')

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, username, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
        ('staff', 'Staff'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    skill = models.ManyToManyField('courses.Category', blank=True, through='InstructorSkill', related_name='instructors')
    is_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)
    no_telp = models.CharField(max_length=20, blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def clean(self):
        super().clean()

    @property
    def is_admin(self):
        return self.role == 'admin'
    @property
    def _is_staff(self):
        return self.role == 'staff'
    @property
    def is_instructor(self):
        return self.role == 'instructor'
    @property
    def is_senior_instructor(self):
        return self.role == 'instructor' and self.instructor_skills.filter(position_status='senior').exists()
    @property
    def is_student(self):
        return self.role == 'student'

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.email
    
class UserProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Profile {self.user.email}"

class InstructorCertificate(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='instructor_certificates'
    )
    title = models.CharField(max_length=255)

    issuing_organization = models.CharField(max_length=255)
    issue_date = models.DateField()
    certificate_file = models.FileField(upload_to='instructor_certificates/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class InstructorSkill(models.Model):
    POSITION_CHOICES = (
        ('junior', 'Junior'),
        ('senior', 'Senior'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='instructor_skills')
    category = models.ForeignKey('courses.Category', on_delete=models.CASCADE, related_name='instructor_skills')
    position_status = models.CharField(max_length=20, choices=POSITION_CHOICES)

    class Meta:
        unique_together = ('user', 'category')

    def __str__(self):
        return f"{self.user.username} - {self.category.name} ({self.get_position_status_display()})"