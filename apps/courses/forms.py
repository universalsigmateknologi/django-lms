from django import forms
from .models import Lesson
from django_ckeditor_5.widgets import CKEditor5Widget

class LessonForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].required = False

    class Meta:
        model = Lesson
        fields = ['title', 'lesson_type', 'video_url', 'content', 'file', 'duration_seconds', 'is_free_preview', 'order']
        widgets = {
            "content": CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"}, config_name="extends"
            )
        }
