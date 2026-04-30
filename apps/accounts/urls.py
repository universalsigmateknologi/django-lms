from django.urls import path
from apps.accounts.views import login_view, verify_email, register, logout_view
urlpatterns = [
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('verify/<uidb64>/<token>/', verify_email, name='verify_email'),
]