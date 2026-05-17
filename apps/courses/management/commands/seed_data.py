import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from apps.courses.models import Category, Course, Module, Lesson
from apps.quizzes.models import Quiz, Question, Answer, QuestionType

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed dummy data for courses and quizzes'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")

        # 1. Create or get Instructor
        instructor, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if _:
            instructor.set_password('admin123')
            instructor.save()

        # 2. Create Category
        category, _ = Category.objects.get_or_create(
            name='Web Development',
            defaults={'slug': 'web-development'}
        )

        # 3. Create Course
        course_title = "Fullstack Web Development Mastery"
        course, created = Course.objects.get_or_create(
            title=course_title,
            defaults={
                'instructor': instructor,
                'category': category,
                'level': 'beginner',
                'price': 500000.00,
                'status': 'published',
                'thumbnail': ContentFile(b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b', name='course_thumb.gif')
            }
        )

        if not created:
            self.stdout.write(f"Course '{course_title}' already exists. Skipping course creation.")
        else:
            self.stdout.write(f"Created course: {course.title}")

        # 4. Create 10 Modules
        for i in range(1, 11):
            module_title = f"Module {i}: Basic Foundations"
            module, m_created = Module.objects.get_or_create(
                course=course,
                order=i,
                defaults={'title': module_title}
            )
            
            if m_created:
                self.stdout.write(f"  Created Module {i}")
                
                # 5. Create 5 Lessons (Materi) for each module
                for j in range(1, 6):
                    Lesson.objects.create(
                        module=module,
                        title=f"Lesson {j}: Understanding Concept {j}",
                        lesson_type='text',
                        content=f"<p>This is the content for lesson {j} in module {i}. It covers fundamental concepts of web development.</p>",
                        duration_seconds=random.randint(300, 1200),
                        order=j
                    )
                
                # 6. Create 1 Lesson (Quiz) for each module
                quiz_lesson = Lesson.objects.create(
                    module=module,
                    title=f"Quiz Module {i}",
                    lesson_type='quiz',
                    content="<p>Test your knowledge of this module.</p>",
                    duration_seconds=600,
                    order=6
                )
                
                # 7. Create Quiz object
                quiz = Quiz.objects.create(
                    lesson=quiz_lesson,
                    title=f"Assessment for Module {i}",
                    description=f"This quiz evaluates your understanding of Module {i}.",
                    pass_score=70,
                    time_limit=600,
                    max_attempts=3
                )
                
                # 8. Create 3 Questions for the quiz
                for k in range(1, 4):
                    question = Question.objects.create(
                        quiz=quiz,
                        question_type=QuestionType.MULTIPLE_CHOICE,
                        text=f"Question {k}: What is the purpose of Module {i} component {k}?",
                        explanation=f"Explanation for question {k} in Module {i}.",
                        points=10,
                        order=k
                    )
                    
                    # 9. Create Answers for the question
                    for l in range(1, 5):
                        is_correct = (l == 1) # Set the first answer as correct
                        Answer.objects.create(
                            question=question,
                            text=f"Option {l} for question {k}",
                            is_correct=is_correct,
                            order=l,
                            feedback=f"Feedback for option {l}"
                        )
                
                self.stdout.write(f"    Added 5 lessons and 1 quiz with 3 questions to Module {i}")
            else:
                self.stdout.write(f"  Module {i} already exists. Skipping.")

        self.stdout.write(self.style.SUCCESS("Successfully seeded dummy data!"))
