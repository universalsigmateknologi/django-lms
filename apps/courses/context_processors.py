from apps.courses.models import Course, Category

def pending_course_verifications_count(request):
    """
    Context processor to provide the count of courses waiting for verification
    to all templates, useful for sidebar notification dots for senior instructors.
    """
    if request.user.is_authenticated and getattr(request.user, 'role', '') == 'instructor':
        # Get categories where the instructor is senior
        senior_categories = Category.objects.filter(
            instructor_skills__user=request.user,
            instructor_skills__position_status='senior'
        )
        if senior_categories.exists():
            count = Course.objects.filter(category__in=senior_categories, status='pending').count()
            return {'pending_course_verifications_count': count}
    return {}
