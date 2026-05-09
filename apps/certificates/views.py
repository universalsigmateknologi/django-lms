from django.db import models
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Certificate

class CertificateListView(LoginRequiredMixin, ListView):
    model = Certificate
    template_name = 'certificates/list.html'
    context_object_name = 'certificates'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = Certificate.objects.filter(student=self.request.user)
        
        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                models.Q(course_title_snapshot__icontains=search_query) |
                models.Q(certificate_number__icontains=search_query)
            )
            
        # Filter by Status
        status_filter = self.request.GET.getlist('status')
        if status_filter:
            status_queries = models.Q()
            if 'active' in status_filter:
                status_queries |= models.Q(is_valid=True)
            if 'expired' in status_filter:
                status_queries |= models.Q(is_valid=False)
            queryset = queryset.filter(status_queries)

        # Filter by Category
        category_filter = self.request.GET.getlist('category')
        if category_filter:
            queryset = queryset.filter(course__category__slug__in=category_filter)
            
        # Filter by Year
        year_filter = self.request.GET.get('year')
        if year_filter:
            queryset = queryset.filter(issued_at__year=year_filter)
            
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_certs = Certificate.objects.filter(student=self.request.user)
        
        # Data for filters
        from apps.courses.models import Category
        context['categories'] = Category.objects.filter(courses__certificates__student=self.request.user).distinct()
        
        # Extract years as integers for easier comparison in template
        issued_dates = user_certs.dates('issued_at', 'year', order='DESC')
        context['years'] = [date.year for date in issued_dates]
        
        # Current filter values
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.getlist('status')
        context['selected_categories'] = self.request.GET.getlist('category')
        context['selected_year'] = self.request.GET.get('year', '')
        context['menu'] = 'certificates'
        
        return context

class CertificateDetailView(LoginRequiredMixin, DetailView):
    model = Certificate
    template_name = 'certificates/detail.html'
    context_object_name = 'certificate'
    slug_field = 'certificate_number'
    slug_url_kwarg = 'cert_number'
    
    def get_queryset(self):
        # Bisa diakses publik untuk keperluan verifikasi sertifikat
        return Certificate.objects.filter(is_valid=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Sertifikat hanya bisa diakses jika is_accessible adalah True
        if not obj.is_accessible:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Sertifikat ini belum dapat diakses atau telah dinonaktifkan.")
        return obj
