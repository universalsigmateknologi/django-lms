from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='index'),
    path('instructor/lessons/<int:lesson_id>/questions/', views.instructor_question_list, name='instructor_question_list'),
    path('instructor/quizzes/<uuid:quiz_id>/settings/', views.instructor_quiz_settings, name='instructor_quiz_settings'),
    path('instructor/quizzes/<uuid:quiz_id>/questions/create/', views.instructor_question_create, name='question_create'),
    path('instructor/questions/<uuid:question_id>/edit/', views.instructor_question_edit, name='question_edit'),
    path('instructor/questions/<uuid:question_id>/delete/', views.instructor_question_delete, name='question_delete'),
]