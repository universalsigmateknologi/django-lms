from django.shortcuts import render

# Create your views here.
def my_course_view(request):
    return render(request, 'enrollments/my_courses.html')

def learn_view(request):
    return render(request, 'enrollments/learn.html')

def i(request):
    return render(request, 'enrollments/quiz_attempt.html')