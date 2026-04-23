def redirect_user_by_role(user):
    if user.role == 'admin':
        return 'dashboard_admin'
    elif user.role == 'instructor':
        return 'dashboard_instructor'
    elif user.role == 'staff':
        return 'dashboard_staff'
    elif user.role == 'student':
        return 'dashboard_student'
    else:
        return 'login'