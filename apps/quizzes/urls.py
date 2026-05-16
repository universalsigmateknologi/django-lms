from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='index'),
    path('instructor/lessons/<int:lesson_id>/questions/', views.instructor_question_list, name='instructor_question_list'),
]