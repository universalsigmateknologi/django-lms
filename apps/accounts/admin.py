from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserProfile


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Field yang ditampilkan di list
    list_display = ('email', 'username', 'role', 'is_verified', 'is_staff', 'is_active')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_active')

    # Field saat edit user
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informasi User', {'fields': ('username', 'role', 'is_verified')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Tanggal', {'fields': ('last_login', 'date_joined')}),
    )

    # Field saat tambah user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'role', 'password1', 'password2', 'is_staff', 'is_active')
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