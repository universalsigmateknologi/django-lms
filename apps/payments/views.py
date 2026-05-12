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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone

from .models import (
    Order, OrderItem, OrderStatus, PaymentSettings,
    ManualPaymentProof, PaymentGateway,
)
from .forms import PaymentProofForm
from apps.courses.models import Course
from apps.enrollments.models import Enrollment

logger = logging.getLogger(__name__)


@login_required
@require_POST
def create_order_view(request, slug):
    """
    POST endpoint: Buat order baru dari halaman course detail.
    Redirects ke halaman pembayaran.
    """
    course = get_object_or_404(Course, slug=slug, is_published=True)

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
        # Redirect ke order yang sudah ada
        return redirect("payments:payment_page", order_number=existing_order.order_number)

    # ── Create Order ──
    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            subtotal=course.price,
            total_amount=course.price,
            currency="IDR",
        )
        OrderItem.objects.create(
            order=order,
            course=course,
            course_title=course.title,
            price_snapshot=course.price,
        )

    messages.success(request, "Order berhasil dibuat! Silakan lakukan pembayaran.")
    return redirect("payments:payment_page", order_number=order.order_number)


@login_required
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
    form = PaymentProofForm()

    # Check if proof already uploaded
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


@login_required
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

    form = PaymentProofForm(request.POST, request.FILES)

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


@login_required
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


@login_required
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

@login_required
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
