from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("staff/", views.staff_analytics_view, name="staff_analytics"),
]
