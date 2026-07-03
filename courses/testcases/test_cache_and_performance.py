from django.test import TestCase, Client
from django.core.cache import cache
from django.contrib.auth.models import User

from courses.models import Course
from courses.cache import (
    get_course_list_cache,
    set_course_list_cache,
    get_course_detail_cache,
    set_course_detail_cache,
    invalidate_course_cache,
)


class CacheUtilityTests(TestCase):
    """Unit test langsung terhadap fungsi-fungsi di courses/cache.py"""

    def setUp(self):
        cache.clear()

    def test_course_list_cache_miss_returns_none(self):
        result = get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at")
        self.assertIsNone(result)

    def test_set_and_get_course_list_cache(self):
        dummy_data = {"total": 2, "page": 1, "per_page": 10, "results": []}
        set_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at", data=dummy_data)
        cached = get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at")
        self.assertEqual(cached, dummy_data)

    def test_course_list_cache_key_is_specific_to_params(self):
        set_course_list_cache(page=1, per_page=10, search="python", ordering="-price", data={"a": 1})
        # Parameter berbeda -> harus cache miss, membuktikan key spesifik per kombinasi filter
        different_params = get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at")
        self.assertIsNone(different_params)

    def test_set_and_get_course_detail_cache(self):
        dummy_detail = {"id": 5, "name": "Machine Learning"}
        set_course_detail_cache(course_id=5, data=dummy_detail)
        cached = get_course_detail_cache(course_id=5)
        self.assertEqual(cached, dummy_detail)

    def test_invalidate_course_cache_clears_detail(self):
        set_course_detail_cache(course_id=7, data={"id": 7})
        invalidate_course_cache(course_id=7)
        self.assertIsNone(get_course_detail_cache(course_id=7))

    def test_invalidate_course_cache_clears_list(self):
        set_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at", data={"total": 1})
        invalidate_course_cache()
        self.assertIsNone(get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at"))


class CacheInvalidationIntegrationTests(TestCase):
    """Test end-to-end: cache terisi lewat API, lalu dihapus otomatis saat data berubah."""

    def setUp(self):
        cache.clear()
        self.django_client = Client()
        self.teacher = User.objects.create_user(
            username="cache_teacher",
            password="teacherpass123",
            is_staff=True,
        )
        Course.objects.create(name="Cache Test Course", price=10000, teacher=self.teacher)

    def test_cache_populated_after_list_request(self):
        # Cache masih kosong sebelum request pertama
        self.assertIsNone(
            get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at")
        )

        response = self.django_client.get("/api/v1/courses?page=1&per_page=10")
        self.assertEqual(response.status_code, 200)

        # Setelah request, cache untuk kombinasi parameter yang sama harus terisi
        cached = get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at")
        self.assertIsNotNone(cached)

    def test_cache_invalidated_after_course_created(self):
        # Isi cache dulu lewat request GET
        self.django_client.get("/api/v1/courses?page=1&per_page=10")
        self.assertIsNotNone(
            get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at")
        )

        # Login sebagai instructor, buat course baru
        login_resp = self.django_client.post(
            "/api/v1/auth/login",
            data={"username": "cache_teacher", "password": "teacherpass123"},
            content_type="application/json",
        )
        token = login_resp.json()["access_token"]

        self.django_client.post(
            "/api/v1/courses",
            data={"name": "New Cached Course", "description": "test", "price": 5000},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

        # Cache untuk kombinasi parameter yang sama harus sudah terhapus
        cached_after = get_course_list_cache(page=1, per_page=10, search=None, ordering="-created_at")
        self.assertIsNone(cached_after)


class NPlusOneQueryTests(TestCase):
    """
    Membuktikan endpoint optimized menggunakan jauh lebih sedikit query dibanding baseline.

    Catatan: lab_views.py memanggil reset_queries() secara internal untuk keperluan
    profiling manual, sehingga CaptureQueriesContext dari luar tidak reliable dipakai
    di sini (log query ke-reset di tengah request). Karena itu test ini membaca
    langsung field `query_count` yang dihitung dan dikembalikan oleh endpoint itu
    sendiri di response JSON -- ini juga angka yang sama yang dipakai untuk
    pembuktian manual di laporan/demo.
    """

    def setUp(self):
        teacher = User.objects.create_user(username="perf_teacher", password="x", is_staff=True)
        # Buat beberapa course supaya N+1 pada baseline benar-benar kelihatan
        for i in range(10):
            Course.objects.create(name=f"Perf Course {i}", price=1000 * i, teacher=teacher)
        self.django_client = Client()

    def test_optimized_uses_fewer_queries_than_baseline(self):
        response_baseline = self.django_client.get("/lab/course-list/baseline/")
        self.assertEqual(response_baseline.status_code, 200)
        baseline_data = response_baseline.json()

        response_optimized = self.django_client.get("/lab/course-list/optimized/")
        self.assertEqual(response_optimized.status_code, 200)
        optimized_data = response_optimized.json()

        baseline_query_count = baseline_data["query_count"]
        optimized_query_count = optimized_data["query_count"]

        # Optimized harus jauh lebih sedikit query dibanding baseline (bukti N+1 fixing)
        self.assertLess(optimized_query_count, baseline_query_count)
        # Optimized seharusnya konstan kecil, tidak scaling dengan jumlah course
        self.assertLessEqual(optimized_query_count, 5)
        # Baseline dengan 10 course seharusnya menghasilkan N+1 (jauh lebih dari 10 query)
        self.assertGreater(baseline_query_count, 10)

    def test_optimized_response_contains_correct_course_count(self):
        response = self.django_client.get("/lab/course-list/optimized/")
        data = response.json()
        self.assertGreaterEqual(data["total"], 10)
