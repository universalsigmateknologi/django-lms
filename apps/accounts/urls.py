from django.urls import path
from apps.accounts.views import (
    login_view, verify_email, register, logout_view, no_permission,
    staff_instructor_list_view, staff_instructor_detail_view, staff_dashboard_view,
    instructor_dashboard_view, instructor_student_list_view, staff_student_list_view
)
urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('verify/<uidb64>/<token>/', verify_email, name='verify_email'),
    path('no-permission/', no_permission, name='no_permission'),
    path('staff/dashboard/', staff_dashboard_view, name='staff_dashboard'),
    path('instructor/dashboard/', instructor_dashboard_view, name='instructor_dashboard'),
    path('instructor/students/', instructor_student_list_view, name='instructor_student_list'),
    path('staff/students/', staff_student_list_view, name='staff_student_list'),
    path('staff/instructors/', staff_instructor_list_view, name='staff_instructor_list'),
    path('staff/instructors/<uuid:pk>/', staff_instructor_detail_view, name='staff_instructor_detail'),
]
