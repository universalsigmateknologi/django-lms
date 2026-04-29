from . import views
from django.urls import path

app_name = 'enrollments'

urlpatterns = [
    path('', views.my_courses_view, name='my_courses'),
]