from . import views
from django.urls import path
urlpatterns = [
    path('', views.my_course_view, name='my_course'),
    path('learn/', views.learn_view, name='learn'),
    path('try/', views.i, name='quiz_attempt'),
]