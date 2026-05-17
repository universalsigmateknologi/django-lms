"""
Views for the payments app — Manual Payment Flow.

Flow:
1. create_order_view  — POST from course detail, creates Order + OrderItem
2. payment_page_view  — Shows bank info, countdown, upload form
3. upload_proof_view   — Handles proof upload, changes status to waiting_verification
4. payment_status_view — Shows current order status (success/waiting/cancelled)
5. order_history_view  — User's order list
"""
import logging
import urllib.parse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import role_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q

from .models import (
    Order, OrderItem, OrderStatus, PaymentSettings,
    ManualPaymentProof, PaymentGateway,
)
from .forms import PaymentProofForm
from apps.courses.models import Course
from apps.enrollments.models import Enrollment

logger = logging.getLogger(__name__)



@role_required(allowed_roles=['student'])
def create_order_view(request, slug):
    """
    GET: Tampilkan halaman pembayaran (bank info + upload form) sebelum order dibuat.
    POST: Buat order sekaligus upload bukti transfer.
    """
    course = get_object_or_404(Course, slug=slug, status='published')

    # ── Guard: Sudah terdaftar? ──
    if Enrollment.objects.filter(student=request.user, course=course).exists():
        messages.info(request, "Kamu sudah terdaftar di kursus ini.")
        return redirect("course_detail", slug=slug)

    # ── Guard: Sudah ada order pending/waiting? ──
    existing_order = Order.objects.filter(
        user=request.user,
        items__course=course,
        status__in=[OrderStatus.PENDING, OrderStatus.WAITING_VERIFICATION],
    ).first()

    if existing_order:
        # Redirect ke order yang sudah ada agar tidak duplikat
        return redirect("payments:payment_page", order_number=existing_order.order_number)

    if request.method == "POST":
        form = PaymentProofForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create Order
                    order = Order.objects.create(
                        user=request.user,
                        subtotal=course.price,
                        total_amount=course.price,
                        currency="IDR",
                    )
                    # 2. Create OrderItem
                    OrderItem.objects.create(
                        order=order,
                        course=course,
                        course_title=course.title,
                        price_snapshot=course.price,
                    )
                    # 3. Save Proof
                    proof = form.save(commit=False)
                    proof.order = order
                    proof.save()

                    # 4. Update order status
                    order.mark_waiting_verification()

                messages.success(request, "Order berhasil dibuat dan bukti transfer telah diupload! Menunggu verifikasi admin.")
                return redirect("payments:payment_page", order_number=order.order_number)
            except Exception as e:
                logger.error(f"Error creating order/uploading proof: {str(e)}")
                messages.error(request, "Terjadi kesalahan saat memproses order. Silakan coba lagi.")
        else:
            messages.error(request, "Upload gagal. Periksa kembali file dan data yang diisi.")
    else:
        form = PaymentProofForm()



    # Context untuk mode "New Order" (order belum ada di DB)
    config = PaymentSettings.load()
    context = {
        "course": course,
        "is_new_order": True,
        "order_items": [
            {
                "course": course,
                "course_title": course.title,
                "price_snapshot": course.price,
            }
        ],
        "subtotal": course.price,
        "total_amount": course.price,
        "config": config,
        "form": form,
        "bank_accounts": config.bank_accounts,
        "time_remaining": 0,
        "whatsapp_url": f"https://wa.me/{config.admin_whatsapp}?text=Halo%20Admin,%20saya%20ingin%20bertanya%20tentang%20kursus%20{urllib.parse.quote(course.title)}",
        "OrderStatus": OrderStatus,
    }
    return render(request, "payments/payment_page.html", context)


@role_required(allowed_roles=['student'])
def payment_page_view(request, order_number):
    """
    Halaman pembayaran: info bank, countdown, form upload bukti transfer.
    """
    order = get_object_or_404(
        Order.objects.select_related("user").prefetch_related("items__course", "payment_proofs"),
        order_number=order_number,
        user=request.user,
    )

    # Auto-expire if past deadline
    if order.status == OrderStatus.PENDING and order.is_expired:
        order.status = OrderStatus.EXPIRED
        order.save(update_fields=["status", "updated_at"])

    config = PaymentSettings.load()
    # Check if proof already uploaded
    existing_proof = order.payment_proofs.first()
    form = PaymentProofForm(instance=existing_proof) if existing_proof else PaymentProofForm()

    context = {


        "order": order,
        "order_items": order.items.select_related("course"),
        "subtotal": order.subtotal,
        "total_amount": order.total_amount,
        "is_new_order": False,
        "config": config,
        "form": form,
        "existing_proof": existing_proof,
        "bank_accounts": config.bank_accounts,
        "time_remaining": order.time_remaining_seconds,
        "whatsapp_url": order.get_whatsapp_url(),
        "OrderStatus": OrderStatus,
    }
    return render(request, "payments/payment_page.html", context)


@role_required(allowed_roles=['student'])
@require_POST
def upload_proof_view(request, order_number):
    """
    Handle upload bukti transfer.
    Ubah status order ke WAITING_VERIFICATION.
    """
    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user,
    )

    # ── Guard: Only pending orders can upload proof ──
    if order.status not in [OrderStatus.PENDING, OrderStatus.WAITING_VERIFICATION]:
        messages.error(request, "Order tidak dalam status yang bisa diupload bukti transfer.")
        return redirect("payments:payment_page", order_number=order_number)

    # ── Guard: Check if expired ──
    if order.status == OrderStatus.PENDING and order.is_expired:
        order.status = OrderStatus.EXPIRED
        order.save(update_fields=["status", "updated_at"])
        messages.error(request, "Order sudah expired. Silakan buat order baru.")
        return redirect("course_detail", slug=order.items.first().course.slug)

    existing_proof = order.payment_proofs.first()
    form = PaymentProofForm(request.POST, request.FILES, instance=existing_proof)

    if form.is_valid():
        with transaction.atomic():
            proof = form.save(commit=False)
            proof.order = order
            proof.save()

            # Update order status
            order.mark_waiting_verification()

        messages.success(request, "Bukti transfer berhasil diupload! Menunggu verifikasi admin.")
        return redirect("payments:payment_page", order_number=order_number)
    else:
        messages.error(request, "Upload gagal. Periksa kembali file dan data yang diisi.")
        # Re-render with form errors
        config = PaymentSettings.load()
        existing_proof = order.payment_proofs.first()
        context = {
            "order": order,
            "order_items": order.items.select_related("course"),
            "config": config,
            "form": form,
            "existing_proof": existing_proof,
            "bank_accounts": config.bank_accounts,
            "time_remaining": order.time_remaining_seconds,
            "whatsapp_url": order.get_whatsapp_url(),
            "OrderStatus": OrderStatus,
        }
        return render(request, "payments/payment_page.html", context)


@role_required(allowed_roles=['student'])
def order_history_view(request):
    """
    Daftar order milik user.
    """
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items__course")
        .order_by("-created_at")
    )

    context = {
        "orders": orders,
        "OrderStatus": OrderStatus,
        "menu": "order_history",
    }
    return render(request, "payments/order_history.html", context)


@role_required(allowed_roles=['student'])
def order_detail_view(request, order_number):
    """
    Detail order tunggal.
    """
    order = get_object_or_404(
        Order.objects.select_related("user")
        .prefetch_related("items__course", "payment_proofs", "payments"),
        order_number=order_number,
        user=request.user,
    )

    context = {
        "order": order,
        "order_items": order.items.select_related("course"),
        "proofs": order.payment_proofs.all(),
        "payments": order.payments.all(),
        "whatsapp_url": order.get_whatsapp_url(),
        "OrderStatus": OrderStatus,
    }
    return render(request, "payments/order_detail.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints (optional AJAX)
# ─────────────────────────────────────────────────────────────────────────────

@role_required(allowed_roles=['student'])
def check_order_status_api(request, order_number):
    """
    AJAX endpoint: cek status order terkini.
    Berguna untuk auto-refresh halaman pembayaran.
    """
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    # Auto-expire
    if order.status == OrderStatus.PENDING and order.is_expired:
        order.status = OrderStatus.EXPIRED
        order.save(update_fields=["status", "updated_at"])

    return JsonResponse({
        "status": order.status,
        "status_display": order.get_status_display(),
        "is_paid": order.is_paid,
        "time_remaining": order.time_remaining_seconds,
    })


@role_required(allowed_roles=['admin', 'staff'])
def staff_order_verification_view(request):
    """
    Halaman untuk staff melakukan verifikasi pesanan.
    """
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    
    orders = Order.objects.select_related('user').prefetch_related(
        'items__course', 'payment_proofs'
    ).order_by('-created_at')
    
    if status_filter != 'all':
        orders = orders.filter(status=status_filter)
        
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
        
    total_count = Order.objects.count()
    waiting_count = Order.objects.filter(status=OrderStatus.WAITING_VERIFICATION).count()
    paid_count = Order.objects.filter(status=OrderStatus.PAID).count()
    failed_count = Order.objects.filter(status__in=[OrderStatus.FAILED, OrderStatus.CANCELLED, OrderStatus.EXPIRED]).count()
    
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': total_count,
        'waiting_count': waiting_count,
        'paid_count': paid_count,
        'failed_count': failed_count,
        'menu': 'staff_orders',
        'OrderStatus': OrderStatus,
    }
    return render(request, 'payments/staff/order_verification.html', context)


@role_required(allowed_roles=['admin', 'staff'])
@require_POST
def staff_verify_order_action(request, pk):
    """
    Action untuk memproses perubahan status verifikasi pesanan oleh admin/staff.
    """
    order = get_object_or_404(Order, pk=pk)
    status = request.POST.get('status')
    admin_note = request.POST.get('admin_note', '').strip()
    
    if status in dict(OrderStatus.choices):
        with transaction.atomic():
            order.status = status
            order.save(update_fields=['status', 'updated_at'])
            
            # Update proof note if there's any proof uploaded
            proof = order.payment_proofs.first()
            if proof:
                proof.admin_note = admin_note
                proof.reviewed_by = request.user
                proof.reviewed_at = timezone.now()
                proof.save(update_fields=['admin_note', 'reviewed_by', 'reviewed_at'])
                
            # If status becomes paid, we can do extra logic like enrolling user etc.
            if status == OrderStatus.PAID:
                order.paid_at = timezone.now()
                order.save(update_fields=['paid_at'])
                
                # Enroll the user to the courses
                for item in order.items.all():
                    Enrollment.objects.get_or_create(
                        student=order.user,
                        course=item.course,
                        defaults={
                            'status': 'active'
                        }
                    )
            
        messages.success(request, f"Status pesanan {order.order_number} berhasil diubah.")
    else:
        messages.error(request, "Status tidak valid.")
        
    return redirect('payments:staff_order_verification')
