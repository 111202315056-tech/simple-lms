from django.test import TestCase, Client
from django.contrib.auth.models import User
from courses.models import Course, CourseMember, CourseContent, Comment
from courses.auth import create_access_token
import json


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="pass123"
        )
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        self.token = create_access_token(self.user.id)
        self.admin_token = create_access_token(self.admin.id)

    def auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_register_success(self):
        res = self.client.post(
            "/api/v1/auth/register",
            data=json.dumps({
                "username": "newuser", "email": "new@test.com",
                "password": "pass123", "first_name": "New", "last_name": "User"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["username"], "newuser")

    def test_register_duplicate_username(self):
        res = self.client.post(
            "/api/v1/auth/register",
            data=json.dumps({
                "username": "testuser", "email": "other@test.com", "password": "pass123"
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_login_success(self):
        res = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({"username": "testuser", "password": "pass123"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.json())

    def test_login_wrong_password(self):
        res = self.client.post(
            "/api/v1/auth/login",
            data=json.dumps({"username": "testuser", "password": "salah"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 401)

    def test_get_me(self):
        res = self.client.get("/api/v1/auth/me", **self.auth_header(self.token))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["username"], "testuser")

    def test_get_me_unauthorized(self):
        res = self.client.get("/api/v1/auth/me")
        self.assertEqual(res.status_code, 401)


class CourseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@test.com", password="pass123"
        )
        self.admin_token = create_access_token(self.admin.id)
        self.student_token = create_access_token(self.student.id)
        self.course = Course.objects.create(
            name="Test Course", description="Desc", price=50000, teacher=self.admin
        )

    def auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_list_courses(self):
        res = self.client.get("/api/v1/courses")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total"], 1)

    def test_list_courses_search(self):
        res = self.client.get("/api/v1/courses?search=Test")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total"], 1)

    def test_list_courses_search_no_result(self):
        res = self.client.get("/api/v1/courses?search=tidakada")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["total"], 0)

    def test_create_course_admin(self):
        res = self.client.post(
            "/api/v1/courses",
            data=json.dumps({"name": "New Course", "description": "Desc", "price": 10000}),
            content_type="application/json",
            **self.auth_header(self.admin_token)
        )
        self.assertEqual(res.status_code, 201)

    def test_create_course_student_forbidden(self):
        res = self.client.post(
            "/api/v1/courses",
            data=json.dumps({"name": "New Course", "description": "Desc", "price": 10000}),
            content_type="application/json",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 403)

    def test_detail_course(self):
        res = self.client.get(f"/api/v1/courses/{self.course.id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Test Course")

    def test_update_course_owner(self):
        res = self.client.patch(
            f"/api/v1/courses/{self.course.id}",
            data=json.dumps({"name": "Updated Course"}),
            content_type="application/json",
            **self.auth_header(self.admin_token)
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["name"], "Updated Course")

    def test_delete_course_owner(self):
        res = self.client.delete(
            f"/api/v1/courses/{self.course.id}",
            **self.auth_header(self.admin_token)
        )
        self.assertEqual(res.status_code, 204)


class EnrollmentTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@test.com", password="pass123"
        )
        self.admin_token = create_access_token(self.admin.id)
        self.student_token = create_access_token(self.student.id)
        self.course = Course.objects.create(
            name="Test Course", description="Desc", price=50000, teacher=self.admin
        )

    def auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_enroll_success(self):
        res = self.client.post(
            f"/api/v1/enrollments?course_id={self.course.id}",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 201)

    def test_enroll_duplicate(self):
        CourseMember.objects.create(course_id=self.course, user_id=self.student, roles="std")
        res = self.client.post(
            f"/api/v1/enrollments?course_id={self.course.id}",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 400)

    def test_my_courses(self):
        CourseMember.objects.create(course_id=self.course, user_id=self.student, roles="std")
        res = self.client.get("/api/v1/enrollments/my-courses", **self.auth_header(self.student_token))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)


class CommentTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@test.com", password="pass123"
        )
        self.admin_token = create_access_token(self.admin.id)
        self.student_token = create_access_token(self.student.id)
        self.course = Course.objects.create(
            name="Test Course", description="Desc", price=0, teacher=self.admin
        )
        self.content = CourseContent.objects.create(
            name="Materi 1", description="Desc", course_id=self.course
        )
        self.membership = CourseMember.objects.create(
            course_id=self.course, user_id=self.student, roles="std"
        )

    def auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_post_comment_enrolled(self):
        res = self.client.post(
            "/api/v1/comments",
            data=json.dumps({"content_id": self.content.id, "comment": "Bagus!"}),
            content_type="application/json",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 201)

    def test_post_comment_not_enrolled(self):
        other = User.objects.create_user(username="other", password="pass123")
        other_token = create_access_token(other.id)
        res = self.client.post(
            "/api/v1/comments",
            data=json.dumps({"content_id": self.content.id, "comment": "Test"}),
            content_type="application/json",
            **self.auth_header(other_token)
        )
        self.assertEqual(res.status_code, 403)

    def test_update_comment_owner(self):
        comment = Comment.objects.create(
            comment="Lama", content_id=self.content, member_id=self.membership
        )
        res = self.client.put(
            f"/api/v1/comments/{comment.id}",
            data=json.dumps({"comment": "Baru"}),
            content_type="application/json",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 200)

    def test_delete_comment_owner(self):
        comment = Comment.objects.create(
            comment="Test", content_id=self.content, member_id=self.membership
        )
        res = self.client.delete(
            f"/api/v1/comments/{comment.id}",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 204)

class ContentTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@test.com", password="pass123"
        )
        self.instructor = User.objects.create_user(
            username="instructor", email="inst@test.com", password="pass123", is_staff=True
        )
        self.admin_token = create_access_token(self.admin.id)
        self.student_token = create_access_token(self.student.id)
        self.instructor_token = create_access_token(self.instructor.id)
        self.course = Course.objects.create(
            name="Test Course", description="Desc", price=0, teacher=self.admin
        )

    def auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_create_content_not_owner(self):
        res = self.client.post(
            "/api/v1/contents",
            data=json.dumps({"name": "Materi 1", "description": "Desc", "course_id": self.course.id}),
            content_type="application/json",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 403)

    def test_delete_content(self):
        content = CourseContent.objects.create(
            name="Hapus", description="Desc", course_id=self.course
        )
        res = self.client.delete(
            f"/api/v1/contents/{content.id}",
            **self.auth_header(self.admin_token)
        )
        self.assertEqual(res.status_code, 204)

    def test_update_me(self):
        res = self.client.put(
            "/api/v1/auth/me",
            data=json.dumps({"first_name": "Admin", "last_name": "User"}),
            content_type="application/json",
            **self.auth_header(self.admin_token)
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["first_name"], "Admin")

    def test_refresh_token(self):
        from courses.auth import create_refresh_token
        refresh = create_refresh_token(self.admin.id)
        res = self.client.post(
            "/api/v1/auth/refresh",
            data=json.dumps({"refresh_token": refresh}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("access_token", res.json())

    def test_detail_course_not_found(self):
        res = self.client.get("/api/v1/courses/99999")
        self.assertEqual(res.status_code, 404)

    def test_enroll_instructor_forbidden(self):
        res = self.client.post(
            f"/api/v1/enrollments?course_id={self.course.id}",
            **self.auth_header(self.instructor_token)
        )
        self.assertEqual(res.status_code, 403)

    def test_delete_course_not_owner(self):
        res = self.client.delete(
            f"/api/v1/courses/{self.course.id}",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 403)

    def test_update_course_not_owner(self):
        res = self.client.patch(
            f"/api/v1/courses/{self.course.id}",
            data=json.dumps({"name": "Hack"}),
            content_type="application/json",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 403)


class CertificateTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="admin123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@test.com", password="pass123"
        )
        self.other_student = User.objects.create_user(
            username="other_student", email="other@test.com", password="pass123"
        )
        self.student_token = create_access_token(self.student.id)
        self.other_student_token = create_access_token(self.other_student.id)
        self.course = Course.objects.create(
            name="Test Course", description="Desc", price=0, teacher=self.admin
        )
        self.membership = CourseMember.objects.create(
            course_id=self.course, user_id=self.student, roles="std"
        )
        self.assistant_membership = CourseMember.objects.create(
            course_id=self.course, user_id=self.other_student, roles="ast"
        )

    def auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_get_certificate_success(self):
        res = self.client.get(
            f"/api/v1/enrollments/{self.membership.id}/certificate",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))

    def test_get_certificate_unauthorized(self):
        res = self.client.get(f"/api/v1/enrollments/{self.membership.id}/certificate")
        self.assertEqual(res.status_code, 401)

    def test_get_certificate_not_owner(self):
        res = self.client.get(
            f"/api/v1/enrollments/{self.membership.id}/certificate",
            **self.auth_header(self.other_student_token)
        )
        self.assertEqual(res.status_code, 403)

    def test_get_certificate_wrong_role(self):
        res = self.client.get(
            f"/api/v1/enrollments/{self.assistant_membership.id}/certificate",
            **self.auth_header(self.other_student_token)
        )
        self.assertEqual(res.status_code, 400)

    def test_get_certificate_not_found(self):
        res = self.client.get(
            "/api/v1/enrollments/99999/certificate",
            **self.auth_header(self.student_token)
        )
        self.assertEqual(res.status_code, 404)
