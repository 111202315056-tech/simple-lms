import csv
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from courses.models import Course, CourseMember


def import_courses(csv_file):
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            teacher = User.objects.get(username=row['teacher_username'])
            course, created = Course.objects.get_or_create(
                name=row['name'],
                defaults={
                    'description': row['description'],
                    'price': int(row['price']),
                    'teacher': teacher,
                }
            )
            status = "[CREATED]" if created else "[EXISTS] "
            print(f"{status} Course: {course.name}")


def import_members(csv_file):
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            course = Course.objects.get(name=row['course_name'])
            user = User.objects.get(username=row['username'])
            member, created = CourseMember.objects.get_or_create(
                course_id=course,
                user_id=user,
                defaults={'roles': row['roles']}
            )
            status = "[CREATED]" if created else "[EXISTS] "
            print(f"{status} Member: {user.username} -> {course.name}")


if __name__ == '__main__':
    print("=== Importing Courses ===")
    import_courses('fixtures/courses.csv')
    print("\n=== Importing Members ===")
    import_members('fixtures/members.csv')
    print("\nImport selesai!")
