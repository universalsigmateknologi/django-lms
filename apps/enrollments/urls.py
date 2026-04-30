from . import views
from django.urls import path

app_name = 'enrollments'

urlpatterns = [
    path('', views.my_courses_view, name='my_courses'),
    path('learn/<slug:course_slug>/<int:lesson_id>/', views.learn_view, name='learn'),
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete_view, name='mark_lesson_complete'),
]