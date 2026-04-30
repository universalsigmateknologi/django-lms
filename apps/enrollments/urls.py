from . import views
from django.urls import path

app_name = 'enrollments'

urlpatterns = [
    path('', views.my_courses_view, name='my_courses'),
    path('learn/<slug:course_slug>/<int:lesson_id>/', views.learn_view, name='learn'),
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete_view, name='mark_lesson_complete'),
    
    # Quiz URLs
    path('learn/<slug:course_slug>/quiz/<uuid:quiz_id>/', views.quiz_start_view, name='quiz_start'),
    path('learn/<slug:course_slug>/quiz/<uuid:quiz_id>/attempt/', views.quiz_attempt_view, name='quiz_attempt'),
    path('learn/<slug:course_slug>/quiz/<uuid:quiz_id>/result/<uuid:attempt_id>/', views.quiz_result_view, name='quiz_result'),
]