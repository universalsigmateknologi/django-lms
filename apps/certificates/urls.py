from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    path('', views.CertificateListView.as_view(), name='list'),
    path('<str:cert_number>/', views.CertificateDetailView.as_view(), name='detail'),
]
