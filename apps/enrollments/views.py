from django.shortcuts import render

# Create your views here.
def my_course_view(request):
    return render(request, 'enrollments/my_courses.html')