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
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'modules': modules,
        'completed_lesson_ids': completed_lesson_ids,
        'total_lessons_count': len(all_lessons),
        'completed_count': len(completed_lesson_ids),
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
def learn_view(request, course_slug, lesson_id):
    course = get_object_or_404(Course, slug=course_slug)
    enrollment = get_object_or_404(Enrollment, course=course, student=request.user)
    lesson = get_object_or_404(Lesson, id=lesson_id, module__course=course)

    # Mark lesson as visited/in progress
    progress, created = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson
    )
    
    context = get_sidebar_context(enrollment, lesson)
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

@login_required
def quiz_start_view(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    enrollment = get_object_or_404(Enrollment, course=quiz.lesson.module.course, student=request.user)
    
    previous_attempts = QuizAttempt.objects.filter(
        enrollment=enrollment,
        quiz=quiz
    ).order_by('-started_at')
    
    last_attempt = previous_attempts.first()
    attempts_count = previous_attempts.count()
    
    context = get_sidebar_context(enrollment, quiz.lesson)
    context.update({
        'quiz': quiz,
        'last_attempt': last_attempt,
        'attempts_count': attempts_count,
        'attempts_left': quiz.max_attempts - attempts_count if quiz.max_attempts > 0 else 'Tidak Terbatas',
    })
    return render(request, 'enrollments/quiz_start.html', context)

@login_required
def quiz_attempt_view(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    enrollment = get_object_or_404(Enrollment, course=quiz.lesson.module.course, student=request.user)
    
    attempt = QuizAttempt.objects.filter(
        enrollment=enrollment,
        quiz=quiz,
        status=QuizAttempt.AttemptStatus.IN_PROGRESS
    ).first()
    
    if not attempt:
        attempts_count = QuizAttempt.objects.filter(enrollment=enrollment, quiz=quiz).count()
        if quiz.max_attempts > 0 and attempts_count >= quiz.max_attempts:
            return redirect('enrollments:quiz_start', quiz_id=quiz.id)
            
        attempt = QuizAttempt.objects.create(
            enrollment=enrollment,
            quiz=quiz,
            status=QuizAttempt.AttemptStatus.IN_PROGRESS
        )

    if request.method == 'POST':
        with transaction.atomic():
            questions = quiz.questions.all()
            earned_points = 0
            
            for question in questions:
                answer_key = f"question_{question.id}"
                selected_answer_ids = request.POST.getlist(answer_key)
                
                record, _ = QuizAnswerRecord.objects.get_or_create(
                    attempt=attempt,
                    question=question
                )
                
                if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
                    if selected_answer_ids:
                        ans_id = selected_answer_ids[0]
                        try:
                            answer = Answer.objects.get(id=ans_id, question=question)
                            record.selected_answer = answer
                            record.is_correct = answer.is_correct
                            if record.is_correct:
                                earned_points += question.points
                        except (Answer.DoesNotExist, ValueError):
                            pass
                    record.save()
                elif question.question_type == QuestionType.ESSAY:
                    record.text_answer = request.POST.get(answer_key, "")
                    record.save()
                elif question.question_type == QuestionType.CODE:
                    record.text_answer = request.POST.get(answer_key, "")
                    record.save()
            
            total_points = sum(q.points for q in questions)
            score = (earned_points / total_points * 100) if total_points > 0 else 0
            attempt.score = score
            attempt.submitted_at = timezone.now()
            attempt.time_spent = (attempt.submitted_at - attempt.started_at).seconds
            
            if score >= quiz.pass_score:
                attempt.status = QuizAttempt.AttemptStatus.PASSED
                progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=quiz.lesson)
                progress.mark_complete()
            else:
                attempt.status = QuizAttempt.AttemptStatus.FAILED
            
            attempt.save()
            return redirect('enrollments:quiz_result', attempt_id=attempt.id)

    questions = quiz.questions.all().prefetch_related('answers')
    if quiz.randomize_questions:
        questions = questions.order_by('?')
        
    context = {
        'quiz': quiz,
        'attempt': attempt,
        'questions': questions,
        'menu': 'quiz_attempt',
    }
    return render(request, 'enrollments/quiz_attempt.html', context)

@login_required
def quiz_result_view(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, enrollment__student=request.user)
    context = get_sidebar_context(attempt.enrollment, attempt.quiz.lesson)
    
    # Format time spent
    minutes = attempt.time_spent // 60
    seconds = attempt.time_spent % 60
    
    context.update({
        'attempt': attempt,
        'quiz': attempt.quiz,
        'time_spent_formatted': f"{minutes}m {seconds}s",
    })
    return render(request, 'enrollments/quiz_result.html', context)
