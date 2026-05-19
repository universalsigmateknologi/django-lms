from django.urls import path
from .views import (
    course_detail_view, course_list_view, landing_view, 
    instructor_course_list, course_create_view, course_edit_view,
    instructor_module_list, instructor_lesson_list, module_create_view,
    module_edit_view, module_delete_view, lesson_create_view,
    lesson_edit_view, lesson_delete_view, course_publish_request,
    staff_course_verification_view, staff_verify_course_action,
    instructor_course_detail
)


urlpatterns = [
    path('', landing_view, name='landing_page'),
    path('courses/', course_list_view, name='course_preview'),
    path('courses/detail/<slug:slug>/', course_detail_view, name='course_detail'),
    path('instructor/courses/', instructor_course_list, name='instructor_course_list'),
    path('instructor/courses/<int:course_id>/modules/', instructor_module_list, name='instructor_module_list'),
    path('instructor/courses/<int:course_id>/modules/create/', module_create_view, name='module_create'),
    path('instructor/modules/edit/<int:pk>/', module_edit_view, name='module_edit'),
    path('instructor/modules/delete/<int:pk>/', module_delete_view, name='module_delete'),
    path('instructor/modules/<int:module_id>/lessons/', instructor_lesson_list, name='instructor_lesson_list'),
    path('instructor/modules/<int:module_id>/lessons/create/', lesson_create_view, name='lesson_create'),
    path('instructor/lessons/edit/<int:pk>/', lesson_edit_view, name='lesson_edit'),
    path('instructor/lessons/delete/<int:pk>/', lesson_delete_view, name='lesson_delete'),

    path('instructor/courses/create/', course_create_view, name='course_create'),
    path('instructor/courses/edit/<int:pk>/', course_edit_view, name='course_edit'),
    path('instructor/courses/publish/<int:pk>/', course_publish_request, name='course_publish'),
    path('instructor/courses/detail/<int:pk>/', instructor_course_detail, name='instructor_course_detail'),

    # Staff Verification Routes
    path('staff/courses/verify/', staff_course_verification_view, name='staff_course_verification'),
    path('staff/courses/verify/<int:pk>/<str:action>/', staff_verify_course_action, name='staff_verify_course_action'),
]




