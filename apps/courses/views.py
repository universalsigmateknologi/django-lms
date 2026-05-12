from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Course, Category, Tag
from django.db.models import Q, Count, Sum, ExpressionWrapper, FloatField, F
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from apps.payments.models import Order, OrderStatus
from apps.enrollments.models import Enrollment, EnrollmentStatus

def landing_view(request):
    return render(request, 'courses/landing.html')

@login_required
def course_list_view(request):

    courses = Course.objects.filter(is_published=True).annotate(
        total_duration_sec=Coalesce(Sum('modules__lessons__duration_seconds'), 0),
        student_count_ann=Count('enrollments', distinct=True)
    ).annotate(
        total_hours_ann=ExpressionWrapper(
            F('total_duration_sec') / 3600.0,
            output_field=FloatField()
        )
    )
    
    categories = Category.objects.annotate(course_count=Count('courses', filter=Q(courses__is_published=True)))
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) | 
            Q(instructor__username__icontains=search_query) |
            Q(instructor__first_name__icontains=search_query) |
            Q(instructor__last_name__icontains=search_query)
        )

    # Filter by Category
    category_slugs = request.GET.getlist('category')
    if category_slugs:
        courses = courses.filter(category__slug__in=category_slugs)

    # Filter by Level
    levels = request.GET.getlist('level')
    if levels:
        courses = courses.filter(level__in=levels)

    # Filter by Price
    price_filter = request.GET.get('price', 'all')
    if price_filter == 'free':
        courses = courses.filter(price=0)
    elif price_filter == 'under200':
        courses = courses.filter(price__lte=200000)
    elif price_filter == 'custom':
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price:
            courses = courses.filter(price__gte=min_price)
        if max_price:
            courses = courses.filter(price__lte=max_price)

    # Filter by Duration
    durations = request.GET.getlist('duration')
    if durations:
        duration_q = Q()
        for d in durations:
            if d == '0-5':
                duration_q |= Q(total_duration_sec__lte=5*3600)
            elif d == '5-20':
                duration_q |= Q(total_duration_sec__gt=5*3600, total_duration_sec__lte=20*3600)
            elif d == '20plus':
                duration_q |= Q(total_duration_sec__gt=20*3600)
        courses = courses.filter(duration_q)

    # Sort
    sort_by = request.GET.get('sort', 'popular')
    if sort_by == 'newest':
        courses = courses.order_by('-created_at')
    elif sort_by == 'price-low':
        courses = courses.order_by('price')
    elif sort_by == 'price-high':
        courses = courses.order_by('-price')
    
    # Pagination
    paginator = Paginator(courses, 6) # Show 6 courses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'levels': Course.LEVEL_CHOICES,
        'selected_categories': category_slugs,
        'selected_levels': levels,
        'selected_price': price_filter,
        'selected_durations': durations,
        'search_query': search_query,
        'sort_by': sort_by,
        'course_count': courses.count(),
        'menu' : 'browse_course',
    }
    return render(request, 'courses/preview.html', context)


def course_detail_view(request, slug):
    course = get_object_or_404(
        Course.objects.annotate(
            total_duration_sec=Coalesce(Sum('modules__lessons__duration_seconds'), 0),
            student_count_ann=Count('enrollments', distinct=True)
        ).annotate(
            total_hours_ann=ExpressionWrapper(
                F('total_duration_sec') / 3600.0,
                output_field=FloatField()
            )
        ), 
        slug=slug
    )
    
    # Prefetch modules and lessons for the curriculum
    modules = course.modules.all().prefetch_related('lessons')
    
    # Calculate stats for curriculum header
    total_lessons = sum(module.lessons.count() for module in modules)
    
    first_lesson_id = None
    # Ensure modules and lessons are ordered correctly
    first_module = course.modules.order_by('order').first()
    if first_module:
        first_lesson = first_module.lessons.order_by('order').first()
        if first_lesson:
            first_lesson_id = first_lesson.id

    user_order = None
    enrollment = None
    if request.user.is_authenticated:
        user_order = Order.objects.filter(
            user=request.user,
            items__course=course
        ).exclude(status=OrderStatus.CANCELLED).order_by('-created_at').first()

        enrollment = Enrollment.objects.filter(
            student=request.user,
            course=course
        ).first()
    
    context = {
        'course': course,
        'modules': modules,
        'total_lessons': total_lessons,
        'first_lesson_id': first_lesson_id,
        'user_order': user_order,
        'enrollment': enrollment,
        'OrderStatus': OrderStatus,
    }
    return render(request, 'courses/detail.html', context)