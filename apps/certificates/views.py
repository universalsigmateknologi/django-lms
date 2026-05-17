from django.db import models
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from apps.accounts.decorators import role_required
from .models import Certificate
from apps.courses.models import Category

@role_required(allowed_roles=['student'])
def certificate_list_view(request):
    queryset = Certificate.objects.filter(student=request.user)
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        queryset = queryset.filter(
            models.Q(course_title_snapshot__icontains=search_query) |
            models.Q(certificate_number__icontains=search_query)
        )
        
    # Filter by Status
    status_filter = request.GET.getlist('status')
    if status_filter:
        status_queries = models.Q()
        if 'active' in status_filter:
            status_queries |= models.Q(is_valid=True)
        if 'expired' in status_filter:
            status_queries |= models.Q(is_valid=False)
        queryset = queryset.filter(status_queries)

    # Filter by Category
    category_filter = request.GET.getlist('category')
    if category_filter:
        queryset = queryset.filter(course__category__slug__in=category_filter)
        
    # Filter by Year
    year_filter = request.GET.get('year')
    if year_filter:
        queryset = queryset.filter(issued_at__year=year_filter)
        
    queryset = queryset.distinct()
    
    # Pagination
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Context data
    user_certs = Certificate.objects.filter(student=request.user)
    categories = Category.objects.filter(courses__certificates__student=request.user).distinct()
    
    # Extract years
    issued_dates = user_certs.dates('issued_at', 'year', order='DESC')
    years = [date.year for date in issued_dates]
    
    context = {
        'certificates': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'years': years,
        'search_query': search_query or '',
        'selected_status': status_filter,
        'selected_categories': category_filter,
        'selected_year': year_filter or '',
        'menu': 'certificates'
    }
    
    return render(request, 'certificates/list.html', context)

@role_required(allowed_roles=['student'])
def certificate_detail_view(request, cert_number):
    # Bisa diakses publik untuk keperluan verifikasi sertifikat (Dibatasi ke student sesuai request)
    certificate = get_object_or_404(Certificate, certificate_number=cert_number, is_valid=True)
    
    # Sertifikat hanya bisa diakses jika is_accessible adalah True
    if not certificate.is_accessible:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Sertifikat ini belum dapat diakses atau telah dinonaktifkan.")
        
    context = {
        'certificate': certificate
    }
    return render(request, 'certificates/detail.html', context)

