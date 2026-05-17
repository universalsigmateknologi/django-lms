from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # ── Order creation (POST from course detail) ──
    path(
        "checkout/<slug:slug>/",
        views.create_order_view,
        name="create_order",
    ),

    # ── Payment page ──
    path(
        "pay/<str:order_number>/",
        views.payment_page_view,
        name="payment_page",
    ),

    # ── Upload proof ──
    path(
        "pay/<str:order_number>/upload/",
        views.upload_proof_view,
        name="upload_proof",
    ),

    # ── Order history ──
    path(
        "orders/",
        views.order_history_view,
        name="order_history",
    ),

    # ── Order detail ──
    path(
        "orders/<str:order_number>/",
        views.order_detail_view,
        name="order_detail",
    ),

    # ── API: check status ──
    path(
        "api/status/<str:order_number>/",
        views.check_order_status_api,
        name="check_status",
    ),

    # ── Staff Order Verification ──
    path(
        "staff/orders/",
        views.staff_order_verification_view,
        name="staff_order_verification",
    ),
    path(
        "staff/orders/verify/<uuid:pk>/",
        views.staff_verify_order_action,
        name="staff_verify_order",
    ),
]
