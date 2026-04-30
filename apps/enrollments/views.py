from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from .models import Enrollment, EnrollmentStatus, LessonProgress, QuizAttempt, QuizAnswerRecord
from apps.courses.models import Course, Lesson, Module
from apps.quizzes.models import Quiz, Question, Answer, QuestionType
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
        # First lesson if no progress
        enrollment.first_lesson = Lesson.objects.filter(module__course=enrollment.course).order_by('module__order', 'order').first()

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
        'menu' : 'my_courses',
    }
    return render(request, 'enrollments/my_courses.html', context)

def get_sidebar_context(enrollment, current_lesson=None):
    course = enrollment.course
    modules = Module.objects.filter(course=course).prefetch_related('lessons').order_by('order')
    
    # Get all progress for this enrollment
    completed_lesson_ids = set(enrollment.lesson_progresses.filter(is_completed=True).values_list('lesson_id', flat=True))
    all_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))
    
    # Determine which lessons are unlocked (sequential)
    unlocked_lesson_ids = set()
    last_completed = True # First lesson is always unlocked
    
    first_locked_lesson = None
    
    for l in all_lessons:
        if last_completed:
            unlocked_lesson_ids.add(l.id)
        elif first_locked_lesson is None:
            first_locked_lesson = l
        
        # Current lesson is also unlocked for viewing (this part is for the sidebar context)
        # However, for access control, we need to be stricter.
        # Let's keep this as is for the sidebar, but we'll use it in learn_view.
            
        last_completed = l.id in completed_lesson_ids

    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
        'completed_lesson_ids': completed_lesson_ids,
        'unlocked_lesson_ids': unlocked_lesson_ids,
        'total_lessons_count': len(all_lessons),
        'completed_count': len(completed_lesson_ids),
        'first_locked_lesson': first_locked_lesson,
    }
    
    if current_lesson:
        current_index = -1
        for i, l in enumerate(all_lessons):
            if l.id == current_lesson.id:
                current_index = i
                break
        
        context.update({
            'lesson': current_lesson,
            'prev_lesson': all_lessons[current_index - 1] if current_index > 0 else None,
            'next_lesson': all_lessons[current_index + 1] if current_index < len(all_lessons) - 1 else None,
            'current_lesson_num': current_index + 1,
        })
        
    return context

@login_required
def mark_lesson_complete_view(request, lesson_id):
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, id=lesson_id)
        enrollment = get_object_or_404(Enrollment, course=lesson.module.course, student=request.user)
        
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson
        )
        
        progress.mark_complete()
        
        # Redirect kembali ke halaman belajar (ini akan otomatis memperbarui sidebar/progress)
        from django.contrib import messages
        messages.success(request, "Materi berhasil ditandai selesai!")
        return redirect('enrollments:learn', course_slug=lesson.module.course.slug, lesson_id=lesson.id)
    
    return redirect('enrollments:my_courses')

@login_required
def learn_view(request, course_slug, lesson_id):
    course = get_object_or_404(Course, slug=course_slug)
    enrollment = get_object_or_404(Enrollment, course=course, student=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)

    # Security Check: Ensure lesson is unlocked
    sidebar_context = get_sidebar_context(enrollment, lesson)
    if lesson.id not in sidebar_context['unlocked_lesson_ids']:
        from django.contrib import messages
        messages.warning(request, "Selesaikan materi sebelumnya terlebih dahulu untuk mengakses materi ini.")
        
        # Find the last unlocked lesson to redirect to
        all_lessons = list(Lesson.objects.filter(module__course=course).order_by('module__order', 'order'))
        last_unlocked_id = all_lessons[0].id
        for l in all_lessons:
            if l.id in sidebar_context['unlocked_lesson_ids']:
                last_unlocked_id = l.id
            else:
                break
        
        return redirect('enrollments:learn', course_slug=course.slug, lesson_id=last_unlocked_id)

    # Mark lesson as visited/in progress
    progress, created = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    
    context = sidebar_context
    context['progress'] = progress

    # Handle YouTube URL transformation
    youtube_id = None
    if lesson.lesson_type == 'video' and lesson.video_url:
        if 'youtube.com/watch?v=' in lesson.video_url:
            youtube_id = lesson.video_url.split('watch?v=')[-1].split('&')[0]
        elif 'youtu.be/' in lesson.video_url:
            youtube_id = lesson.video_url.split('/')[-1]
        elif 'youtube.com/embed/' in lesson.video_url:
            youtube_id = lesson.video_url.split('embed/')[-1]
    
    context['youtube_id'] = youtube_id
    
    return render(request, 'enrollments/learn.html', context)
