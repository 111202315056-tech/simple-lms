import os
import django
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from courses.models import Course, CourseMember, CourseContent, Comment

print("=== Membuat Data Seed ===")

# Buat 20 teacher
teachers = []
for i in range(1, 21):
    user, created = User.objects.get_or_create(
        username=f'teacher{i:02d}',
        defaults={
            'email': f'teacher{i:02d}@lms.id',
            'first_name': f'Teacher',
            'last_name': f'{i:02d}',
            'is_staff': True,
        }
    )
    if created:
        user.set_password('password123')
        user.save()
    teachers.append(user)
print(f"✓ {len(teachers)} teachers")

# Buat 100 students
students = []
for i in range(1, 101):
    user, created = User.objects.get_or_create(
        username=f'student{i:03d}',
        defaults={
            'email': f'student{i:03d}@lms.id',
            'first_name': f'Student',
            'last_name': f'{i:03d}',
        }
    )
    students.append(user)
print(f"✓ {len(students)} students")

# Buat 100 courses (bulk_create)
existing = Course.objects.count()
if existing < 100:
    courses_to_create = []
    for i in range(existing + 1, 101):
        courses_to_create.append(Course(
            name=f'Kursus {i:03d}',
            description=f'Deskripsi kursus nomor {i}',
            price=random.choice([0, 25000, 50000, 75000, 100000]),
            teacher=random.choice(teachers),
        ))
    Course.objects.bulk_create(courses_to_create)
    print(f"✓ {len(courses_to_create)} courses dibuat")
else:
    print(f"✓ {existing} courses sudah ada")

courses = list(Course.objects.all())

# Buat 500 course members (bulk_create)
existing_members = CourseMember.objects.count()
if existing_members < 500:
    members_to_create = []
    pairs = set()
    while len(members_to_create) < 500:
        course = random.choice(courses)
        student = random.choice(students)
        key = (course.id, student.id)
        if key not in pairs:
            pairs.add(key)
            members_to_create.append(CourseMember(
                course_id=course,
                user_id=student,
                roles=random.choice(['std', 'std', 'std', 'ast']),
            ))
    CourseMember.objects.bulk_create(members_to_create, ignore_conflicts=True)
    print(f"✓ {len(members_to_create)} members dibuat")

members = list(CourseMember.objects.all())

# Buat 300 course contents (bulk_create)
existing_contents = CourseContent.objects.count()
if existing_contents < 300:
    contents_to_create = []
    for i in range(existing_contents + 1, 301):
        contents_to_create.append(CourseContent(
            name=f'Materi {i:03d}',
            description=f'Deskripsi materi {i}',
            course_id=random.choice(courses),
        ))
    CourseContent.objects.bulk_create(contents_to_create)
    print(f"✓ {len(contents_to_create)} contents dibuat")

contents = list(CourseContent.objects.all())

# Buat 1000 comments (bulk_create)
existing_comments = Comment.objects.count()
if existing_comments < 1000:
    comments_to_create = []
    for i in range(existing_comments + 1, 1001):
        comments_to_create.append(Comment(
            content_id=random.choice(contents),
            member_id=random.choice(members),
            comment=f'Komentar nomor {i} - ini adalah contoh komentar pada materi',
        ))
    Comment.objects.bulk_create(comments_to_create)
    print(f"✓ {len(comments_to_create)} comments dibuat")

print("\n=== Seed selesai! ===")
print(f"  Courses  : {Course.objects.count()}")
print(f"  Members  : {CourseMember.objects.count()}")
print(f"  Contents : {CourseContent.objects.count()}")
print(f"  Comments : {Comment.objects.count()}")
