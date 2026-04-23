from django.urls import path
from apps.accounts.views import login_view, verify_email, register
urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register, name='register'),
    path('verify/<uidb64>/<token>/', verify_email, name='verify_email'),
]