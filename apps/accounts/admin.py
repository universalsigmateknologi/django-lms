from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError
from .models import CustomUser, UserProfile, InstructorSkill


class InstructorSkillFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        
        # Check if the parent instance is an instructor
        if self.instance and self.instance.role == 'instructor':
            # Check if there are any active skills in the formset
            has_skills = False
            for form in self.forms:
                if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                    if form.cleaned_data.get('category'):
                        has_skills = True
                        break
            
            from apps.courses.models import Category
            if Category.objects.exists() and not has_skills:
                raise ValidationError('Instruktur wajib memiliki minimal satu skill beserta status jabatannya!')


class InstructorSkillInline(admin.TabularInline):
    model = InstructorSkill
    formset = InstructorSkillFormSet
    extra = 1


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    inlines = [InstructorSkillInline]
    filter_horizontal = ('groups', 'user_permissions')

    # Field yang ditampilkan di list
    list_display = ('email', 'username', 'role', 'is_verified', 'is_staff', 'is_active')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active')

    # Field saat edit user
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informasi User', {'fields': ('username', 'role', 'is_verified', 'no_telp')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Tanggal', {'fields': ('last_login', 'date_joined')}),
    )

    # Field saat tambah user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'role', 'password1', 'password2', 'is_staff', 'is_active', 'no_telp')
        }),
    )

    search_fields = ('email', 'username')
    ordering = ('email',)
    readonly_fields = ('date_joined', 'last_login')


# Register model
admin.site.register(CustomUser, CustomUserAdmin)


# Optional: tampilkan profile di admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar')
    search_fields = ('user__email',)