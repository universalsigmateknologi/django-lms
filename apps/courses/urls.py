from django.urls import path
from apps.courses.views import course_list_view, landing_view
urlpatterns = [
    path('', landing_view, name='landing_page'),
    path('courses/', course_list_view, name='course_preview'),
]