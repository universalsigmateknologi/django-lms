from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def landing_view(request):
    return render(request, 'courses/landing.html')

@login_required(login_url='login')
def course_list_view(request):
    # Placeholder for course list view
    return render(request, 'courses/preview.html')

def course_detail_view(request, course_id):
    # Placeholder for course detail view
    return render(request, 'courses/detail.html', {'course_id': course_id})

def search_results_view(request):
    # Placeholder for search results view
    return render(request, 'courses/search.html')