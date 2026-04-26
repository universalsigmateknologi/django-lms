from django.urls import path
from apps.courses.views import landing_view
urlpatterns = [
    path('', landing_view, name='landing_page'),
]