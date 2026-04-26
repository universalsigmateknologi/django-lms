from django.shortcuts import render

def landing_view(request):
    return render(request, 'courses/landing.html')

def course_list_view(request):
    # Placeholder for course list view
    return render(request, 'courses/preview.html')

def course_detail_view(request, course_id):
    # Placeholder for course detail view
    return render(request, 'courses/detail.html', {'course_id': course_id})