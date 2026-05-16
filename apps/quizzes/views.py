from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Quiz, Question
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