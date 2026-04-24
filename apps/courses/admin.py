from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Lesson, Course, Category, Module

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'lesson_type')
    
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    search_fields = ('title', 'description')
    
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    
@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')