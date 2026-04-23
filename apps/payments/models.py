import uuid
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class Currency(models.TextChoices):
    IDR = "IDR", _("Indonesian Rupiah")
    USD = "USD", _("US Dollar")
    EUR = "EUR", _("Euro")


class PaymentGateway(models.TextChoices):
    MIDTRANS = "midtrans", _("Midtrans")
    STRIPE   = "stripe",   _("Stripe")
    PAYPAL   = "paypal",   _("PayPal")
    MANUAL   = "manual",   _("Manual Transfer")


class OrderStatus(models.TextChoices):
    PENDING   = "pending",   _("Pending")
    PAID      = "paid",      _("Paid")
    FAILED    = "failed",    _("Failed")
    CANCELLED = "cancelled", _("Cancelled")
    REFUNDED  = "refunded",  _("Refunded")
    EXPIRED   = "expired",   _("Expired")


class PaymentStatus(models.TextChoices):
    PENDING   = "pending",   _("Pending")
    SUCCESS   = "success",   _("Success")
    FAILED    = "failed",    _("Failed")
    REFUNDED  = "refunded",  _("Refunded")


class CouponType(models.TextChoices):
    PERCENTAGE = "percentage", _("Percentage (%)")
    FLAT       = "flat",       _("Flat Amount")


# ─────────────────────────────────────────────────────────────────────────────

class Coupon(models.Model):
    """
    Kode diskon yang bisa dipakai saat checkout.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code            = models.CharField(_("coupon code"), max_length=50, unique=True)
    coupon_type     = models.CharField(
                        _("type"), max_length=20,
                        choices=CouponType.choices,
                        default=CouponType.PERCENTAGE,
                      )
    discount_value  = models.DecimalField(
                        _("discount value"), max_digits=10, decimal_places=2,
                        validators=[MinValueValidator(0)],
                        help_text=_("Nilai persen (0–100) atau nominal flat"),
                      )
    max_discount    = models.DecimalField(
                        _("max discount amount"), max_digits=12, decimal_places=2,
                        null=True, blank=True,
                        help_text=_("Batas maksimal potongan untuk tipe persentase"),
                      )
    min_purchase    = models.DecimalField(
                        _("minimum purchase"), max_digits=12, decimal_places=2,
                        default=0,
                        help_text=_("Minimum total order untuk bisa pakai kupon ini"),
                      )
    # Batasan penggunaan
    max_usage       = models.PositiveIntegerField(
                        _("max usage"), default=0,
                        help_text=_("0 = tidak terbatas"),
                      )
    used_count      = models.PositiveIntegerField(_("used count"), default=0)
    max_usage_per_user = models.PositiveSmallIntegerField(
                           _("max usage per user"), default=1,
                         )
    # Kursus spesifik (null = berlaku untuk semua kursus)
    applicable_courses = models.ManyToManyField(
                           "courses.Course",
                           blank=True,
                           related_name="coupons",
                           verbose_name=_("applicable courses"),
                         )
    is_active       = models.BooleanField(_("is active"), default=True)
    valid_from      = models.DateTimeField(_("valid from"), default=timezone.now)
    valid_until     = models.DateTimeField(_("valid until"), null=True, blank=True)
    created_by      = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL,
                        null=True,
                        related_name="created_coupons",
                      )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = "coupons"
        verbose_name = _("coupon")
        verbose_name_plural = _("coupons")
        ordering     = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.get_coupon_type_display()} — {self.discount_value})"

    @property
    def is_valid(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_usage > 0 and self.used_count >= self.max_usage:
            return False
        return True

    def calculate_discount(self, amount: float) -> float:
        """Hitung nominal diskon dari total amount."""
        if self.coupon_type == CouponType.PERCENTAGE:
            discount = float(amount) * float(self.discount_value) / 100
            if self.max_discount:
                discount = min(discount, float(self.max_discount))
        else:
            discount = float(self.discount_value)
        return min(discount, float(amount))  # diskon tidak boleh melebihi total


class Order(models.Model):
    """
    Satu order bisa berisi lebih dari satu kursus (bundle).
    Dibuat saat student klik checkout.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number  = models.CharField(
                      _("order number"), max_length=30,
                      unique=True, editable=False,
                    )
    user          = models.ForeignKey(
                      settings.AUTH_USER_MODEL,
                      on_delete=models.CASCADE,
                      related_name="orders",
                    )
    status        = models.CharField(
                      _("status"), max_length=20,
                      choices=OrderStatus.choices,
                      default=OrderStatus.PENDING,
                    )
    currency      = models.CharField(
                      _("currency"), max_length=3,
                      choices=Currency.choices,
                      default=Currency.IDR,
                    )
    subtotal      = models.DecimalField(
                      _("subtotal"), max_digits=12, decimal_places=2,
                      default=0,
                    )
    discount_amount = models.DecimalField(
                        _("discount amount"), max_digits=12, decimal_places=2,
                        default=0,
                      )
    total_amount  = models.DecimalField(
                      _("total amount"), max_digits=12, decimal_places=2,
                      default=0,
                    )
    coupon        = models.ForeignKey(
                      Coupon,
                      on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name="orders",
                    )
    notes         = models.TextField(_("notes"), blank=True)
    created_at    = models.DateTimeField(_("created at"), default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)
    paid_at       = models.DateTimeField(_("paid at"), null=True, blank=True)
    expired_at    = models.DateTimeField(_("expired at"), null=True, blank=True)

    class Meta:
        db_table     = "orders"
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering     = ["-created_at"]
        indexes      = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["order_number"]),
        ]

    def __str__(self):
        return f"Order {self.order_number} — {self.user.email}"

    def save(self, *args, **kwargs):
        # Auto-generate order number saat pertama kali dibuat
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_order_number() -> str:
        import random, string
        prefix = timezone.now().strftime("%Y%m%d")
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{prefix}-{suffix}"

    def mark_paid(self):
        self.status  = OrderStatus.PAID
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at"])

    def mark_failed(self):
        self.status = OrderStatus.FAILED
        self.save(update_fields=["status"])

    def mark_refunded(self):
        self.status = OrderStatus.REFUNDED
        self.save(update_fields=["status"])

    @property
    def is_paid(self) -> bool:
        return self.status == OrderStatus.PAID


class OrderItem(models.Model):
    """
    Detail setiap kursus yang ada dalam satu Order.
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order          = models.ForeignKey(
                       Order,
                       on_delete=models.CASCADE,
                       related_name="items",
                     )
    course         = models.ForeignKey(
                       "courses.Course",
                       on_delete=models.PROTECT,  # jangan hapus course yang sudah dibeli
                       related_name="order_items",
                     )
    # Snapshot harga saat transaksi — penting agar histori tidak berubah
    course_title   = models.CharField(_("course title snapshot"), max_length=255)
    price_snapshot = models.DecimalField(
                       _("price at purchase"), max_digits=12, decimal_places=2,
                     )
    currency       = models.CharField(_("currency"), max_length=3, default=Currency.IDR)

    class Meta:
        db_table        = "order_items"
        verbose_name    = _("order item")
        verbose_name_plural = _("order items")
        unique_together = ("order", "course")

    def __str__(self):
        return f"{self.order.order_number} | {self.course_title}"

    def save(self, *args, **kwargs):
        # Auto-snapshot judul dan harga kursus
        if not self.course_title:
            self.course_title = self.course.title
        if not self.price_snapshot:
            self.price_snapshot = self.course.price
        super().save(*args, **kwargs)


class Payment(models.Model):
    """
    Record transaksi pembayaran dari gateway.
    Satu Order bisa punya lebih dari satu Payment
    (misal: gagal lalu coba lagi).
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order           = models.ForeignKey(
                        Order,
                        on_delete=models.CASCADE,
                        related_name="payments",
                      )
    gateway         = models.CharField(
                        _("payment gateway"), max_length=20,
                        choices=PaymentGateway.choices,
                      )
    status          = models.CharField(
                        _("status"), max_length=20,
                        choices=PaymentStatus.choices,
                        default=PaymentStatus.PENDING,
                      )
    # ID transaksi dari gateway (Midtrans order_id / Stripe payment_intent_id)
    transaction_id  = models.CharField(
                        _("transaction ID"), max_length=100,
                        unique=True, blank=True, null=True,
                      )
    amount          = models.DecimalField(
                        _("amount"), max_digits=12, decimal_places=2,
                      )
    currency        = models.CharField(_("currency"), max_length=3, default=Currency.IDR)
    payment_method  = models.CharField(
                        _("payment method"), max_length=50, blank=True,
                        help_text=_("Contoh: credit_card, gopay, bank_transfer"),
                      )
    # Raw response dari gateway untuk audit
    gateway_response = models.JSONField(
                         _("gateway response"), default=dict, blank=True,
                       )
    paid_at         = models.DateTimeField(_("paid at"), null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = "payments"
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering     = ["-created_at"]
        indexes      = [
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["order", "status"]),
        ]

    def __str__(self):
        return f"{self.gateway} | {self.transaction_id} | {self.status}"


class Refund(models.Model):
    """
    Permintaan refund dari student atau inisiasi admin.
    """
    class RefundStatus(models.TextChoices):
        REQUESTED = "requested", _("Requested")
        APPROVED  = "approved",  _("Approved")
        REJECTED  = "rejected",  _("Rejected")
        PROCESSED = "processed", _("Processed")

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment        = models.OneToOneField(
                       Payment,
                       on_delete=models.CASCADE,
                       related_name="refund",
                     )
    requested_by   = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True,
                       related_name="refund_requests",
                     )
    reviewed_by    = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.SET_NULL,
                       null=True, blank=True,
                       related_name="refund_reviews",
                     )
    status         = models.CharField(
                       _("status"), max_length=20,
                       choices=RefundStatus.choices,
                       default=RefundStatus.REQUESTED,
                     )
    reason         = models.TextField(_("reason"))
    refund_amount  = models.DecimalField(
                       _("refund amount"), max_digits=12, decimal_places=2,
                     )
    admin_note     = models.TextField(_("admin note"), blank=True)
    requested_at   = models.DateTimeField(_("requested at"), default=timezone.now)
    processed_at   = models.DateTimeField(_("processed at"), null=True, blank=True)

    class Meta:
        db_table     = "refunds"
        verbose_name = _("refund")
        verbose_name_plural = _("refunds")
        ordering     = ["-requested_at"]

    def __str__(self):
        return f"Refund {self.payment.transaction_id} — {self.status}"


class InstructorRevenue(models.Model):
    """
    Catatan bagi hasil revenue per instruktur per order item.
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instructor     = models.ForeignKey(
                       settings.AUTH_USER_MODEL,
                       on_delete=models.CASCADE,
                       related_name="revenues",
                       limit_choices_to={"role": "instructor"},
                     )
    order_item     = models.OneToOneField(
                       OrderItem,
                       on_delete=models.CASCADE,
                       related_name="instructor_revenue",
                     )
    revenue_pct    = models.PositiveSmallIntegerField(
                       _("revenue share (%)"), default=70,
                       validators=[MinValueValidator(1), MaxValueValidator(100)],
                     )
    gross_amount   = models.DecimalField(_("gross amount"), max_digits=12, decimal_places=2)
    net_amount     = models.DecimalField(_("net amount (after share)"), max_digits=12, decimal_places=2)
    is_paid_out    = models.BooleanField(_("is paid out"), default=False)
    paid_out_at    = models.DateTimeField(_("paid out at"), null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = "instructor_revenues"
        verbose_name = _("instructor revenue")
        verbose_name_plural = _("instructor revenues")
        ordering     = ["-created_at"]

    def __str__(self):
        return f"{self.instructor.email} | {self.net_amount} | {'Paid' if self.is_paid_out else 'Unpaid'}"