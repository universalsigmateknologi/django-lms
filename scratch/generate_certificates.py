import os
import django
from django.utils import timezone
import sys

sys.path.append('d:\\MyApp\\Django\\Django-lms')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.courses.models import Course
from apps.enrollments.models import Enrollment, EnrollmentStatus
from apps.certificates.models import Certificate, CertificateTemplate

User = get_user_model()

def generate_dummy_data():
    # 1. Pastikan ada template default
    template = CertificateTemplate.objects.filter(is_default=True).first()
    if not template:
        print("Creating default Certificate Template...")
        template = CertificateTemplate.objects.create(name="Default Template", is_default=True)

    # 2. Get a student
    student = User.objects.filter(role='student').first()
    if not student:
        print("No student found. Creating one...")
        student = User.objects.create_user(username='student_cert', email='student_cert@example.com', password='password123', role='student')

    # 3. Get some courses
    courses = Course.objects.all()[:3]
    if not courses:
        print("No courses found. Please create courses first.")
        return

    certificates_created = 0

    for course in courses:
        # 4. Create or update enrollment
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={'status': EnrollmentStatus.COMPLETED, 'progress_pct': 100.0, 'completed_at': timezone.now()}
        )
        
        if not created:
            if enrollment.status != EnrollmentStatus.COMPLETED:
                enrollment.status = EnrollmentStatus.COMPLETED
                enrollment.progress_pct = 100.0
                enrollment.completed_at = timezone.now()
                enrollment.save()
            
        # The signal auto_generate_certificate will run and create the Certificate automatically!
        # But if it didn't (e.g. status was already COMPLETED), let's ensure certificate exists:
        if not Certificate.objects.filter(student=student, course=course).exists():
            Certificate.objects.create(
                student=student,
                course=course,
                enrollment=enrollment,
                template=template,
            )

        certificates_created += 1

    print(f"Successfully processed {certificates_created} enrollments for {student.email}.")
    print(f"Certificates for {student.email}: {Certificate.objects.filter(student=student).count()}")

if __name__ == '__main__':
    generate_dummy_data()
