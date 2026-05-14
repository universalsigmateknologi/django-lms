from django.urls import path
from apps.courses.views import course_detail_view, course_list_view, landing_view, instructor_course_list, course_create_view, course_edit_view

urlpatterns = [
    path('', landing_view, name='landing_page'),
    path('courses/', course_list_view, name='course_preview'),
    path('courses/detail/<slug:slug>/', course_detail_view, name='course_detail'),
    path('instructor/courses/', instructor_course_list, name='instructor_course_list'),
    path('instructor/courses/create/', course_create_view, name='course_create'),
    path('instructor/courses/edit/<int:pk>/', course_edit_view, name='course_edit'),
]