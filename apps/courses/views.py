from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import role_required
from .models import Course, Category, Tag, Module, Lesson
from .forms import LessonForm

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

    # Filter by Type (Online/Offline)
    is_online_filter = request.GET.get('is_online', 'all')
    if is_online_filter == 'online':
        courses = courses.filter(is_online=True)
    elif is_online_filter == 'offline':
        courses = courses.filter(is_online=False)

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
        'selected_is_online': is_online_filter,
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

@login_required
@role_required(allowed_roles=['instructor'])
def instructor_course_list(request):
    courses_list = Course.objects.filter(instructor=request.user).annotate(
        total_duration_sec=Coalesce(Sum('modules__lessons__duration_seconds'), 0),
        student_count_ann=Count('enrollments', distinct=True),
        module_count=Count('modules', distinct=True)
    ).annotate(
        total_hours_ann=ExpressionWrapper(
            F('total_duration_sec') / 3600.0,
            output_field=FloatField()
        )
    ).order_by('-created_at')

    # Status counts
    active_count = Course.objects.filter(instructor=request.user, is_published=True).count()
    draft_count = Course.objects.filter(instructor=request.user, is_published=False).count()
    total_count = Course.objects.filter(instructor=request.user).count()

    # Filter by status if requested
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        courses_list = courses_list.filter(is_published=True)
    elif status_filter == 'draft':
        courses_list = courses_list.filter(is_published=False)

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        courses_list = courses_list.filter(title__icontains=search_query)

    # Pagination
    paginator = Paginator(courses_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_count': total_count,
        'active_count': active_count,
        'draft_count': draft_count,
        'status_filter': status_filter,
        'search_query': search_query,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'menu': 'instructor_courses',
    }
    return render(request, 'courses/instructor/course_list.html', context)

@login_required
@role_required(allowed_roles=['instructor'])
def course_create_view(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        level = request.POST.get('level')
        price = request.POST.get('price')
        is_online = request.POST.get('is_online') == 'on'
        description = request.POST.get('description')
        thumbnail = request.FILES.get('thumbnail')
        tag_ids = request.POST.getlist('tags')

        category = get_object_or_404(Category, id=category_id)
        
        course = Course.objects.create(
            instructor=request.user,
            title=title,
            category=category,
            level=level,
            price=price,
            is_online=is_online,
            description=description,
            thumbnail=thumbnail,
            is_published=False # Default to draft
        )
        
        if tag_ids:
            course.tags.set(tag_ids)
            
        return redirect('instructor_course_list')
    
    return redirect('instructor_course_list')

@login_required
@role_required(allowed_roles=['instructor'])
def course_edit_view(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    
    if request.method == 'POST':
        course.title = request.POST.get('title')
        category_id = request.POST.get('category')
        course.level = request.POST.get('level')
        course.price = request.POST.get('price')
        course.is_online = request.POST.get('is_online') == 'on'
        course.description = request.POST.get('description')
        
        thumbnail = request.FILES.get('thumbnail')
        if thumbnail:
            course.thumbnail = thumbnail
            
        course.category = get_object_or_404(Category, id=category_id)
        course.save()
        
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            course.tags.set(tag_ids)
        else:
            course.tags.clear()
            
        return redirect('instructor_course_list')
    
    return redirect('instructor_course_list')

@login_required
@role_required(allowed_roles=['instructor'])
def instructor_module_list(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    modules_list = Module.objects.filter(course=course).order_by('order')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        modules_list = modules_list.filter(title__icontains=search_query)

    # Pagination
    paginator = Paginator(modules_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'course': course,
        'page_obj': page_obj,
        'search_query': search_query,
        'menu': 'instructor_courses',
    }
    return render(request, 'courses/instructor/module_list.html', context)

@login_required
@role_required(allowed_roles=['instructor'])
def instructor_lesson_list(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)
    lessons_list = Lesson.objects.filter(module=module).order_by('order')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        lessons_list = lessons_list.filter(title__icontains=search_query)

    # Pagination
    paginator = Paginator(lessons_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'module': module,
        'page_obj': page_obj,
        'search_query': search_query,
        'form': LessonForm(),
        'menu': 'instructor_courses',
    }

    return render(request, 'courses/instructor/lesson_list.html', context)

@login_required
@role_required(allowed_roles=['instructor'])
def module_create_view(request, course_id):
    course = get_object_or_404(Course, id=course_id, instructor=request.user)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        order = request.POST.get('order')
        
        # If order is not provided, get the next one
        if not order:
            from django.db.models import Max
            max_order = Module.objects.filter(course=course).aggregate(Max('order'))['order__max'] or 0
            order = max_order + 1
            
        Module.objects.create(
            course=course,
            title=title,
            order=order
        )
        return redirect('instructor_module_list', course_id=course.id)
        
    return redirect('instructor_module_list', course_id=course.id)

@login_required
@role_required(allowed_roles=['instructor'])
def module_edit_view(request, pk):
    module = get_object_or_404(Module, pk=pk, course__instructor=request.user)
    
    if request.method == 'POST':
        module.title = request.POST.get('title')
        module.order = request.POST.get('order')
        module.save()
        return redirect('instructor_module_list', course_id=module.course.id)
        
    return redirect('instructor_module_list', course_id=module.course.id)

@login_required
@role_required(allowed_roles=['instructor'])
def module_delete_view(request, pk):
    module = get_object_or_404(Module, pk=pk, course__instructor=request.user)
    course_id = module.course.id
    
    if request.method == 'POST':
        password = request.POST.get('password')
        if request.user.check_password(password):
            module.delete()
            # Reorder remaining modules? Maybe not necessary if we allow gaps, 
            # but let's keep it simple for now.
            return redirect('instructor_module_list', course_id=course_id)
        else:
            # Handle incorrect password - maybe with a message
            from django.contrib import messages
            messages.error(request, 'Password salah. Modul gagal dihapus.')
            
    return redirect('instructor_module_list', course_id=course_id)

@login_required
@role_required(allowed_roles=['instructor'])
def lesson_create_view(request, module_id):
    module = get_object_or_404(Module, id=module_id, course__instructor=request.user)
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.save()
            return redirect('instructor_lesson_list', module_id=module.id)
    else:
        # Calculate next order
        from django.db.models import Max
        max_order = Lesson.objects.filter(module=module).aggregate(Max('order'))['order__max'] or 0
        next_order = max_order + 1
        form = LessonForm()
        
    context = {
        'module': module,
        'form': form,
        'next_order': next_order,
        'menu': 'instructor_courses',
    }
    return render(request, 'courses/instructor/lesson_create.html', context)


