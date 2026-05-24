from django.test import TestCase
from django.contrib.auth.models import User
from courses.models import Course, CourseMember


class CourseModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='pass1234',
            email='teacher@example.com',
            is_staff=True,
        )

    def test_course_creation(self):
        course = Course.objects.create(
            name='Django Testing',
            description='Belajar testing',
            price=150000,
            teacher=self.teacher,
        )
        self.assertEqual(course.name, 'Django Testing')
        self.assertEqual(course.teacher, self.teacher)
        self.assertIsNotNone(course.created_at)
        self.assertIsNotNone(course.updated_at)

    def test_course_str(self):
        course = Course.objects.create(name='Python', teacher=self.teacher)
        self.assertEqual(str(course), 'Python')

    def test_course_default_price(self):
        course = Course.objects.create(name='Free Course', teacher=self.teacher)
        self.assertEqual(course.price, 10000)


class CourseMemberModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='pass1234',
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username='student1',
            password='pass1234',
        )
        self.course = Course.objects.create(
            name='Django Course',
            teacher=self.teacher,
        )

    def test_course_member_creation(self):
        member = CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
            roles='std',
        )
        self.assertEqual(member.course_id, self.course)
        self.assertEqual(member.user_id, self.student)
        self.assertEqual(member.roles, 'std')

    def test_course_member_str(self):
        member = CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
            roles='std',
        )
        self.assertIn(str(self.student), str(member))
        self.assertIn(str(self.course), str(member))

    def test_default_role_is_std(self):
        member = CourseMember.objects.create(
            course_id=self.course,
            user_id=self.student,
        )
        self.assertEqual(member.roles, 'std')

    def test_role_choices(self):
        self.assertIn(('std', 'Siswa'), CourseMember._meta.get_field('roles').choices)
        self.assertIn(('ast', 'Asisten'), CourseMember._meta.get_field('roles').choices)
