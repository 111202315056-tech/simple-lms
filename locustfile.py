from locust import HttpUser, task, between
import random


class LMSUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        """Login saat user mulai"""
        res = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        if res.status_code == 200:
            self.token = res.json()["access_token"]

    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def list_courses(self):
        """Task paling sering - list courses"""
        self.client.get("/api/v1/courses")

    @task(3)
    def list_courses_with_search(self):
        """Search courses"""
        keywords = ["python", "django", "api", "belajar"]
        self.client.get(f"/api/v1/courses?search={random.choice(keywords)}")

    @task(2)
    def list_courses_with_filter(self):
        """Filter by price"""
        self.client.get("/api/v1/courses?min_price=0&max_price=100000")

    @task(2)
    def detail_course(self):
        """Lihat detail course"""
        self.client.get("/api/v1/courses/1")

    @task(1)
    def get_me(self):
        """Get current user"""
        if self.token:
            self.client.get("/api/v1/auth/me", headers=self.auth_headers())

    @task(1)
    def my_courses(self):
        """Lihat enrolled courses"""
        if self.token:
            self.client.get("/api/v1/enrollments/my-courses", headers=self.auth_headers())


class AnonymousUser(HttpUser):
    wait_time = between(1, 5)

    @task(10)
    def browse_courses(self):
        self.client.get("/api/v1/courses")

    @task(3)
    def search_courses(self):
        self.client.get("/api/v1/courses?search=python")

    @task(1)
    def view_course(self):
        self.client.get("/api/v1/courses/1")
