from . import views
from django.urls import path
urlpatterns = [
    path('', views.my_course_view, name='my_course'),
]