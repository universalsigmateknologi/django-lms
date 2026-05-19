from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta


class CourseAnalyticService:
    @staticmethod
    def snapshot(course) -> dict:
        """Hitung semua statistik kursus secara real-time."""
        from apps.enrollments.models import Enrollment, EnrollmentStatus
        from apps.quizzes.models import QuizAttempt

        enrollments = Enrollment.objects.filter(course=course)
        today       = timezone.now().date()
        week_ago    = timezone.now() - timedelta(days=7)

        return {
            "total_enrollments": enrollments.count(),
            "new_enrollments":   enrollments.filter(enrolled_at__date=today).count(),
            "total_completions": enrollments.filter(status=EnrollmentStatus.COMPLETED).count(),
            "avg_progress_pct":  enrollments.aggregate(avg=Avg("progress_pct"))["avg"] or 0.0,
            "completion_rate":   (
                enrollments.filter(status=EnrollmentStatus.COMPLETED).count() /
                enrollments.count() * 100
            ) if enrollments.count() > 0 else 0.0,
            "drop_rate": (
                enrollments.filter(status=EnrollmentStatus.DROPPED).count() /
                enrollments.count() * 100
            ) if enrollments.count() > 0 else 0.0,
        }


class PlatformAnalyticService:
    @staticmethod
    def snapshot() -> dict:
        """Hitung statistik platform secara real-time."""
        from apps.accounts.models import CustomUser
        from apps.courses.models import Course
        from apps.enrollments.models import Enrollment, EnrollmentStatus, QuizAttempt
        from apps.payments.models import Order, OrderStatus
        from apps.certificates.models import Certificate

        today    = timezone.now().date()
        week_ago = timezone.now() - timedelta(days=7)

        total_revenue = Order.objects.filter(
            status=OrderStatus.PAID
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        new_revenue = Order.objects.filter(
            status=OrderStatus.PAID,
            paid_at__date=today,
        ).aggregate(total=Sum("total_amount"))["total"] or 0

        quiz_attempts  = QuizAttempt.objects.all()
        passed_attempts = quiz_attempts.filter(
            status=QuizAttempt.AttemptStatus.PASSED
        ).count()

        return {
            "total_users":       CustomUser.objects.count(),
            "new_users":         CustomUser.objects.filter(date_joined__date=today).count(),
            "total_students":    CustomUser.objects.filter(role='student').count(),
            "total_instructors": CustomUser.objects.filter(role='instructor').count(),
            "total_courses":     Course.objects.count(),
            "published_courses": Course.objects.filter(status='published').count(),
            "total_enrollments": Enrollment.objects.count(),
            "new_enrollments":   Enrollment.objects.filter(enrolled_at__date=today).count(),
            "total_completions": Enrollment.objects.filter(status=EnrollmentStatus.COMPLETED).count(),
            "total_revenue":     total_revenue,
            "new_revenue":       new_revenue,
            "total_quiz_attempts": quiz_attempts.count(),
            "quiz_pass_rate": (
                passed_attempts / quiz_attempts.count() * 100
            ) if quiz_attempts.count() > 0 else 0.0,
            "total_certificates": Certificate.objects.count(),
            "new_certificates":   Certificate.objects.filter(issued_at__date=today).count(),
        }