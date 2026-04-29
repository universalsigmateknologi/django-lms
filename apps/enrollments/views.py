from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Enrollment, EnrollmentStatus
from apps.courses.models import Lesson
from django.db.models import Count, Q

@login_required
def my_courses_view(request):
    enrollments = Enrollment.objects.filter(student=request.user).select_related(
        'course', 'course__instructor'
    ).order_by('-enrolled_at')

    # Add extra data to each enrollment for the template
    for enrollment in enrollments:
        # Total lessons in the course
        enrollment.total_lessons = Lesson.objects.filter(module__course=enrollment.course).count()
        # Lessons completed by the student
        enrollment.completed_lessons = enrollment.lesson_progresses.filter(is_completed=True).count()
        # Latest lesson accessed
        enrollment.latest_progress = enrollment.lesson_progresses.select_related('lesson').order_by('-updated_at').first()

    # Statistics for the banner (Mocked for now as per template design)
    stats = {
        'streak': 14,
        'hours_week': 12.5,
        'hours_total': 186,
        'certificates': enrollments.filter(status=EnrollmentStatus.COMPLETED).count()
    }

    context = {
        'enrollments': enrollments,
        'stats': stats,
        'EnrollmentStatus': EnrollmentStatus,
    }
    return render(request, 'enrollments/my_courses.html', context)
