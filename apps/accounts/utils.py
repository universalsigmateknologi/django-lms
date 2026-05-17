# untuk sementara semuanya di redirect ke course_preview, nanti bisa disesuaikan lagi sesuai kebutuhan
def redirect_user_by_role(user):
    if user.role == 'admin':
        return 'course_preview'
    elif user.role == 'instructor':
        return 'instructor_course_list'
    elif user.role == 'staff':
        return 'payments:staff_order_verification'
    elif user.role == 'student':
        return 'course_preview'
    else:
        return 'login'