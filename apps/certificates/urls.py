from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    path('', views.certificate_list_view, name='list'),
    path('<str:cert_number>/', views.certificate_detail_view, name='detail'),
]

