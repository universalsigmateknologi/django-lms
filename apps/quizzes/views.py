from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Quiz, Question, QuestionType, Answer
from apps.courses.models import Lesson
from apps.accounts.decorators import role_required

# Create your views here.
def index(request):
    return render(request, 'quizzes/start.html')

@role_required(allowed_roles=['instructor'])
def instructor_question_list(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Dapatkan atau buat Quiz terkait lesson ini
    quiz, created = Quiz.objects.get_or_create(
        lesson=lesson,
        defaults={'title': lesson.title}
    )
    
    search_query = request.GET.get('search', '')
    questions_list = Question.objects.filter(quiz=quiz).order_by('order')
    
    if search_query:
        questions_list = questions_list.filter(
            Q(text__icontains=search_query)
        )
    
    paginator = Paginator(questions_list, 10) # 10 soal per halaman
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'lesson': lesson,
        'quiz': quiz,
        'page_obj': page_obj,
        'search_query': search_query,
        'menu': 'instructor_courses',
    }
    return render(request, 'quizzes/instructor/question_list.html', context)

@role_required(allowed_roles=['instructor'])
def instructor_quiz_settings(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    lesson = quiz.lesson
    
    if request.method == 'POST':
        quiz.title = request.POST.get('title')
        quiz.description = request.POST.get('description')
        quiz.pass_score = int(request.POST.get('pass_score', 70))
        quiz.time_limit = int(request.POST.get('time_limit', 0))
        quiz.max_attempts = int(request.POST.get('max_attempts', 0))
        quiz.randomize_questions = request.POST.get('randomize_questions') == 'on'
        quiz.randomize_answers = request.POST.get('randomize_answers') == 'on'
        quiz.show_feedback = request.POST.get('show_feedback') == 'on'
        quiz.is_active = request.POST.get('is_active') == 'on'
        quiz.save()
        
        messages.success(request, 'Pengaturan quiz berhasil diperbarui.')
        return redirect('instructor_quiz_settings', quiz_id=quiz.id)
        
    context = {
        'quiz': quiz,
        'lesson': lesson,
        'menu': 'instructor_courses',
    }
    return render(request, 'quizzes/instructor/quiz_settings.html', context)

@role_required(allowed_roles=['instructor'])
def instructor_question_create(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    lesson = quiz.lesson
    
    if request.method == 'POST':
        question_type = request.POST.get('question_type')
        text = request.POST.get('text')
        points = int(request.POST.get('points', 1))
        explanation = request.POST.get('explanation', '')
        
        # Create Question
        question = Question.objects.create(
            quiz=quiz,
            question_type=question_type,
            text=text,
            points=points,
            explanation=explanation,
            order=quiz.questions.count() + 1
        )
        
        # Handle Answers based on type
        if question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
            answer_texts = request.POST.getlist('answer_text')
            correct_indices = request.POST.getlist('is_correct') # ini berisi value dari radio/checkbox
            
            # Jika radio button (true_false), is_correct akan berisi satu nilai string index
            # Jika checkbox (multiple_choice bisa saja multiple correct? model Answer punya is_correct boolean)
            # User minta multiple choice, biasanya 1 benar. Tapi kita dukung list.
            
            for i, ans_text in enumerate(answer_texts):
                is_correct = str(i) in correct_indices
                Answer.objects.create(
                    question=question,
                    text=ans_text,
                    is_correct=is_correct,
                    order=i
                )
        elif question_type == QuestionType.CODE:
            question.code_language = request.POST.get('code_language')
            question.code_template = request.POST.get('code_template')
            question.save()
            
        messages.success(request, 'Soal berhasil ditambahkan.')
        return redirect('instructor_question_list', lesson_id=lesson.id)
        
    context = {
        'quiz': quiz,
        'lesson': lesson,
        'question_types': QuestionType.choices,
        'menu': 'instructor_courses',
    }
    return render(request, 'quizzes/instructor/question_create.html', context)