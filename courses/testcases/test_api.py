import unittest
import json

from django.test import TestCase, Client
from django.contrib.auth.models import User
from ninja.testing import TestClient
from courses.apiv1 import apiv1
from courses.models import Course, CourseMember, CourseContent, Comment


class BaseAPITestCase(TestCase):
    def setUp(self):
        self.client = TestClient(apiv1)
        self.django_client = Client()
        self.teacher = User.objects.create_user(
            username='teacher1',
            password='teacherpass123',
            email='teacher@example.com',
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username='student1',
            password='studentpass123',
            email='student@example.com',
        )
        self.course = Course.objects.create(
            name='Testing Course',
            description='Course untuk testing',
            price=100000,
            teacher=self.teacher,
        )
        CourseMember.objects.create(
            course_id=self.course,
            user_id=self.teacher,
            roles='ast',
        )

    def login(self, username, password):
        response = self.client.post(
            'auth/login',
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        return response.json()['access_token']

    def login_tokens(self, username, password):
        response = self.client.post(
            'auth/login',
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def auth_headers(self, token):
        return {'Authorization': f'Bearer {token}'}


class AuthAPITests(BaseAPITestCase):
    def test_register_user(self):
        response = self.client.post(
            'auth/register',
            data=json.dumps({
                'username': 'newstudent',
                'email': 'newstudent@example.com',
                'password': 'StrongP@ssw0rd',
                'first_name': 'New',
                'last_name': 'Student',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['username'], 'newstudent')

    def test_login_and_refresh_token(self):
        tokens = self.login_tokens('teacher1', 'teacherpass123')
        self.assertIsInstance(tokens['access_token'], str)
        self.assertIsInstance(tokens['refresh_token'], str)

        response = self.client.post(
            'auth/refresh',
            data=json.dumps({'refresh_token': tokens['refresh_token']}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.json())

    def test_me_endpoint_requires_auth(self):
        response = self.client.get('auth/me')
        self.assertEqual(response.status_code, 401)

    def test_me_endpoint_returns_user(self):
        token = self.login('teacher1', 'teacherpass123')
        response = self.client.get('auth/me', headers=self.auth_headers(token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['username'], 'teacher1')


class CourseAPITests(BaseAPITestCase):
    def test_list_courses(self):
        response = self.client.get('courses')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertGreaterEqual(data['total'], 1)

    def test_create_update_delete_course(self):
        token = self.login('teacher1', 'teacherpass123')
        response = self.client.post(
            'courses',
            data=json.dumps({'name': 'New Course', 'description': 'deskripsi', 'price': 50000}),
            content_type='application/json',
            headers=self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 201)
        course_id = response.json()['id']

        response = self.client.patch(
            f'courses/{course_id}',
            data=json.dumps({'name': 'Updated Course'}),
            content_type='application/json',
            headers=self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], 'Updated Course')

        response = self.client.delete(f'courses/{course_id}', headers=self.auth_headers(token))
        self.assertEqual(response.status_code, 204)

    def test_student_cannot_create_course(self):
        token = self.login('student1', 'studentpass123')
        response = self.client.post(
            'courses',
            data=json.dumps({'name': 'Bad Course', 'description': 'desc', 'price': 50000}),
            content_type='application/json',
            headers=self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_can_create_content(self):
        token = self.login('teacher1', 'teacherpass123')
        response = self.client.post(
            'contents',
            data=json.dumps({
                'name': 'Lesson API',
                'description': 'Konten via API',
                'course_id': self.course.id,
            }),
            content_type='application/json',
            headers=self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['name'], 'Lesson API')


class EnrollmentAndCommentAPITests(BaseAPITestCase):
    def test_student_enroll_and_comment(self):
        token = self.login('student1', 'studentpass123')
        enroll_response = self.client.post(
            f'enrollments?course_id={self.course.id}',
            headers=self.auth_headers(token),
        )
        self.assertEqual(enroll_response.status_code, 201)
        self.assertTrue(CourseMember.objects.filter(course_id=self.course, user_id=self.student).exists())

        content = CourseContent.objects.create(
            name='Lesson 1',
            description='Intro',
            course_id=self.course,
        )
        response = self.client.post(
            'comments',
            data=json.dumps({'content_id': content.id, 'comment': 'Nice content'}),
            content_type='application/json',
            headers=self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Comment.objects.count(), 1)

    def test_non_member_cannot_comment(self):
        token = self.login('student1', 'studentpass123')
        content = CourseContent.objects.create(
            name='Lesson 2',
            description='Intro',
            course_id=self.course,
        )
        response = self.client.post(
            'comments',
            data=json.dumps({'content_id': content.id, 'comment': 'Spam'}),
            content_type='application/json',
            headers=self.auth_headers(token),
        )
        self.assertEqual(response.status_code, 403)

    @unittest.skip("Popular courses dari MongoDB - tidak bisa ditest di unit test")
    def test_popular_courses_updated_after_enrollment(self):
        token = self.login('student1', 'studentpass123')
        enroll_response = self.client.post(
            f'enrollments?course_id={self.course.id}',
            headers=self.auth_headers(token),
        )
        self.assertEqual(enroll_response.status_code, 201)

        popular_response = self.client.get('analytics/popular-courses', headers=self.auth_headers(token))
        self.assertEqual(popular_response.status_code, 200)
        popular_data = popular_response.json()
        self.assertTrue(any(item['_id'] == self.course.id for item in popular_data))

    @unittest.skip("Endpoint visit/history belum diimplementasi")
    def test_visit_course_session_history(self):
        token = self.login('teacher1', 'teacherpass123')
        visit_response = self.django_client.post(
            f'courses/{self.course.id}/visit',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(visit_response.status_code, 200)
        history_response = self.django_client.get(
            'my-history',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()['visited_courses'], [self.course.id])
