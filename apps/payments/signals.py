"""
Signals for the payments app.

- Automatic enrollment creation when Order status changes to 'paid'.
- Uses Django signals for loose coupling between payments and enrollments.
"""
import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Order, OrderStatus

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Order)
def handle_order_status_change(sender, instance, **kwargs):
    """
    Saat status Order berubah menjadi PAID:
    1. Buat Enrollment otomatis untuk setiap course di order.
    2. Buat Payment record jika belum ada.

    Saat status Order berubah menjadi CANCELLED:
    - Log cancellation (enrollment tidak dibuat).
    """
    if not instance.pk:
        return  # Skip new objects

    try:
        old_instance = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return

    old_status = old_instance.status
    new_status = instance.status

    if old_status == new_status:
        return  # No status change

    # ── PAID ──────────────────────────────────────────────
    if new_status == OrderStatus.PAID and old_status != OrderStatus.PAID:
        _create_enrollments(instance)
        _create_payment_record(instance)
        logger.info(f"Order {instance.order_number} marked as PAID. Enrollments created.")

    # ── CANCELLED ─────────────────────────────────────────
    elif new_status == OrderStatus.CANCELLED:
        logger.info(f"Order {instance.order_number} has been CANCELLED.")


def _create_enrollments(order):
    """Buat Enrollment untuk semua course dalam order."""
    from apps.enrollments.models import Enrollment, EnrollmentStatus

    for item in order.items.select_related("course"):
        enrollment, created = Enrollment.objects.get_or_create(
            student=order.user,
            course=item.course,
            defaults={
                "status": EnrollmentStatus.ACTIVE,
                "enrolled_at": timezone.now(),
                "order": order,
            },
        )
        if created:
            logger.info(
                f"Enrollment created: {order.user.email} → {item.course.title}"
            )
        else:
            # User might have been previously dropped/expired – reactivate
            if enrollment.status in (EnrollmentStatus.DROPPED, EnrollmentStatus.EXPIRED):
                enrollment.status = EnrollmentStatus.ACTIVE
                enrollment.order = order
                enrollment.save(update_fields=["status", "order"])
                logger.info(
                    f"Enrollment reactivated: {order.user.email} → {item.course.title}"
                )


def _create_payment_record(order):
    """Buat Payment record untuk order yang di-paid secara manual."""
    from .models import Payment, PaymentGateway, PaymentStatus

    # Skip jika sudah ada payment record yang sukses
    if order.payments.filter(status=PaymentStatus.SUCCESS).exists():
        return

    Payment.objects.create(
        order=order,
        gateway=PaymentGateway.MANUAL,
        status=PaymentStatus.SUCCESS,
        transaction_id=f"MANUAL-{order.order_number}",
        amount=order.total_amount,
        currency=order.currency,
        payment_method="manual_transfer",
        paid_at=timezone.now(),
        gateway_response={"verified_by": "admin", "method": "manual_transfer"},
    )
