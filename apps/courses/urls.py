from django.urls import path
from apps.courses.views import course_detail_view, course_list_view, landing_view, search_results_view
urlpatterns = [
    path('', landing_view, name='landing_page'),
    path('preview/', course_list_view, name='course_preview'),
    path('search/', search_results_view, name='search_results'),
    path('detail/<int:course_id>/', course_detail_view, name='course_detail'),
]