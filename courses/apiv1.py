import os
from datetime import datetime
from ninja import NinjaAPI, File, Field, FilterSchema, Query, UploadedFile, Schema
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Count, Q
from django.http import FileResponse
from typing import Any, Dict, List, Optional
from .models import Course, CourseMember, CourseContent, Comment
from .schemas import (
    RegisterIn, LoginIn, TokenOut, RefreshIn, AccessTokenOut,
    UserOut, UserUpdateIn,
    CourseIn, CoursePatchIn, CourseOut, DetailCourseOut, PaginatedCourseOut,
    CourseContentIn, CourseContentOut, CourseContentPatchIn,
    PaginatedCourseContentOut, CourseOutV2,
    EnrollmentIn, EnrollmentOut, CommentIn, CommentOut, CommentUpdateIn,
    PopularCourseOut, TaskStatusOut,
)
from .auth import (
    jwt_auth, create_access_token, create_refresh_token,
    decode_token, get_user_role, is_course_owner,
    is_instructor, is_admin, is_student,
)
from .helpers import get_object_or_404
from .mongo import (
    log_activity,
    record_learning_analytics,
    get_popular_courses,
    get_user_activity_summary,
    get_daily_activity_summary,
)
from .tasks import (
    send_enrollment_email,
    generate_certificate,
    export_course_report,
    update_course_statistics,
)
from celery.result import AsyncResult
from .cache import (
    make_course_list_key,
    get_cached_course_list,
    set_cached_course_list,
    invalidate_course_cache,
    get_cached_course_detail,
    set_cached_course_detail,
    increment_course_popularity,
    remove_course_popularity,
    get_top_popular_courses,
)


class AnonThrottle(AnonRateThrottle):
    rate = "20/minute"


class AuthThrottle(AuthRateThrottle):
    rate = "100/minute"


class LoginThrottle(AnonRateThrottle):
    rate = "5/minute"


class UploadThrottle(AuthRateThrottle):
    rate = "10/hour"


class CourseFilter(FilterSchema):
    price: Optional[int] = None
    created_at: Optional[datetime] = None
    teacher: Optional[str] = Field(None, q=["teacher__username__icontains", "teacher__first_name__icontains", "teacher__last_name__icontains"])
    search: Optional[str] = Field(None, q=["name__icontains", "description__icontains"])

    def filter_price(self, value: Optional[int]) -> Q:
        return Q(price__gt=value) if value is not None else Q()

    def filter_created_at(self, value: Optional[datetime]) -> Q:
        return Q(created_at__gt=value) if value else Q()


class ContentFilter(FilterSchema):
    course_id: Optional[int] = None
    search: Optional[str] = Field(None, q=["name__icontains", "description__icontains"])

    def filter_course_id(self, value: Optional[int]) -> Q:
        return Q(course_id=value) if value is not None else Q()


class ActivityLogIn(Schema):
    action: str
    course_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AnalyticsUserSummaryOut(Schema):
    user_id: int
    total_actions: int
    actions_breakdown: Dict[str, int]
    recent_activities: List[Dict[str, Any]]


class AnalyticsDailySummaryOut(Schema):
    date: str
    total_actions: int
    unique_user_count: int


apiv1 = NinjaAPI(
    title="Simple LMS API",
    version="1.0.0",
    description="REST API dengan JWT Authentication dan Role-Based Access Control",
    docs_url="/docs",
    throttle=[AnonThrottle(), AuthThrottle()],
)


apiv2 = NinjaAPI(
    title="Simple LMS API v2",
    version="2.0.0",
    description="Simple LMS API versi 2 dengan response yang richer",
    docs_url="/docs",
    throttle=[AnonThrottle(), AuthThrottle()],
)


@apiv1.post("register/", response={201: UserOut}, tags=["Auth"])
@apiv1.post("auth/register/", response={201: UserOut}, tags=["Auth"])
def register(request, data: RegisterIn):
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah digunakan")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah digunakan")
    if len(data.password) < 8:
        raise HttpError(400, "Password harus minimal 8 karakter")
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=make_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
    )
    return 201, {
        "id": user.id, "username": user.username, "email": user.email,
        "first_name": user.first_name, "last_name": user.last_name,
        "role": get_user_role(user),
    }


@apiv1.post("auth/sign-in/", response=TokenOut, tags=["Auth"])
@apiv1.post("auth/login/", response=TokenOut, tags=["Auth"])
def login(request, data: LoginIn):
    try:
        user = User.objects.get(username=data.username)
    except User.DoesNotExist:
        raise HttpError(401, "Username atau password salah")
    if not check_password(data.password, user.password):
        raise HttpError(401, "Username atau password salah")
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


@apiv1.post("auth/token-refresh/", response=AccessTokenOut, tags=["Auth"])
@apiv1.post("auth/refresh/", response=AccessTokenOut, tags=["Auth"])
def refresh_token(request, data: RefreshIn):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HttpError(401, "Refresh token tidak valid")
    try:
        user = User.objects.get(pk=payload["sub"])
    except User.DoesNotExist:
        raise HttpError(401, "User tidak ditemukan")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@apiv1.get("auth/me/", response=UserOut, auth=jwt_auth, tags=["Auth"])
def get_me(request):
    user = request.auth
    return {
        "id": user.id, "username": user.username, "email": user.email,
        "first_name": user.first_name, "last_name": user.last_name,
        "role": get_user_role(user),
    }


@apiv1.put("auth/me/", response=UserOut, auth=jwt_auth, tags=["Auth"])
def update_me(request, data: UserUpdateIn):
    user = request.auth
    if data.email:
        if User.objects.exclude(pk=user.pk).filter(email=data.email).exists():
            raise HttpError(400, "Email sudah digunakan")
        user.email = data.email
    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.password:
        user.password = make_password(data.password)
    user.save()
    return {
        "id": user.id, "username": user.username, "email": user.email,
        "first_name": user.first_name, "last_name": user.last_name,
        "role": get_user_role(user),
    }


@apiv1.get("courses/", response=PaginatedCourseOut, tags=["Courses"])
def list_courses(
    request,
    filters: CourseFilter = Query(...),
    ordering: str = "-created_at",
    page: int = 1,
    per_page: int = 10,
):
    cache_key = make_course_list_key(
        ordering=ordering,
        page=page,
        per_page=per_page,
        price=filters.price,
        created_at=filters.created_at,
        search=filters.search,
        teacher=filters.teacher,
    )
    cached_data = get_cached_course_list(cache_key)
    if cached_data is not None:
        return cached_data

    qs = Course.objects.select_related("teacher").all()
    qs = filters.filter(qs)
    allowed_ordering = ["name", "-name", "price", "-price", "created_at", "-created_at"]
    if ordering not in allowed_ordering:
        ordering = "-created_at"
    qs = qs.order_by(ordering)
    total = qs.count()
    offset = (page - 1) * per_page
    results = list(qs[offset:offset + per_page])
    response_data = {"total": total, "page": page, "per_page": per_page, "results": results}
    set_cached_course_list(cache_key, response_data)
    return response_data


@apiv1.get("courses/{id}/", response=DetailCourseOut, tags=["Courses"])
def detail_course(request, id: int):
    cached_data = get_cached_course_detail(id)
    if cached_data is not None:
        return cached_data
    try:
        course = Course.objects.select_related("teacher").prefetch_related("coursecontent_set").get(pk=id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")
    course_data = {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "price": course.price,
        "image": course.image.url if course.image else None,
        "teacher": {
            "id": course.teacher.id,
            "username": course.teacher.username,
            "first_name": course.teacher.first_name,
            "last_name": course.teacher.last_name,
        },
        "created_at": course.created_at,
        "updated_at": course.updated_at,
        "coursecontent_set": [
            {"id": content.id, "name": content.name}
            for content in course.coursecontent_set.all()
        ],
    }
    set_cached_course_detail(id, course_data)
    return course_data


@apiv1.put("courses/{id}/", response=CourseOut, auth=jwt_auth, tags=["Courses"])
def replace_course(request, id: int, data: CourseIn):
    course = get_object_or_404(Course, pk=id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course atau Admin yang bisa mengubah")
    if data.price < 0:
        raise HttpError(400, "Harga tidak boleh negatif")
    course.name = data.name
    course.description = data.description
    course.price = data.price
    course.save()
    invalidate_course_cache(course.id)
    return course


@apiv1.post("courses/", response={201: CourseOut}, auth=jwt_auth, tags=["Courses"])
def create_course(request, data: CourseIn):
    is_instructor(request)
    if data.price < 0:
        raise HttpError(400, "Harga tidak boleh negatif")
    course = Course.objects.create(
        name=data.name, description=data.description,
        price=data.price, teacher=request.auth,
    )
    invalidate_course_cache()
    return 201, course


@apiv1.patch("courses/{id}/", response=CourseOut, auth=jwt_auth, tags=["Courses"])
def update_course(request, id: int, data: CoursePatchIn):
    course = get_object_or_404(Course, pk=id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course atau Admin yang bisa mengubah")
    payload = data.dict(exclude_unset=True)
    if "name" in payload:
        course.name = payload["name"]
    if "description" in payload:
        course.description = payload["description"]
    if "price" in payload:
        if payload["price"] < 0:
            raise HttpError(400, "Harga tidak boleh negatif")
        course.price = payload["price"]
    course.save()
    invalidate_course_cache(course.id)
    return course


@apiv1.delete("courses/{id}/", response={204: None}, auth=jwt_auth, tags=["Courses"])
def delete_course(request, id: int):
    course = get_object_or_404(Course, pk=id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course atau Admin yang bisa menghapus")
    course.delete()
    invalidate_course_cache(id)
    remove_course_popularity(id)
    return 204, None


@apiv1.get("courses/popular/", response=List[PopularCourseOut], tags=["Courses"])
def popular_courses(request, limit: int = 10):
    return get_top_popular_courses(limit=limit)


@apiv1.post("analytics/log/", response={201: dict}, auth=jwt_auth, tags=["Analytics"])
def log_analytics(request, data: ActivityLogIn):
    log_activity(
        user_id=request.auth.id,
        username=request.auth.username,
        action=data.action,
        metadata={
            **({'course_name': data.course_name} if data.course_name else {}),
            **(data.metadata or {}),
        } if data.course_name or data.metadata else {},
    )
    return 201, {"status": "logged"}


@apiv1.get("analytics/popular-courses/", auth=jwt_auth, tags=["Analytics"])
def analytics_popular_courses(request, limit: int = 5):
    if not is_admin(request.auth):
        raise HttpError(403, "Hanya admin yang boleh melihat course populer")
    return get_popular_courses(limit=limit)


@apiv1.get("analytics/user-activity/", auth=jwt_auth, response=AnalyticsUserSummaryOut, tags=["Analytics"])
def analytics_user_activity(request):
    if not is_admin(request.auth):
        raise HttpError(403, "Hanya admin yang boleh melihat ringkasan aktivitas user")
    return get_user_activity_summary(request.auth.id)


@apiv1.get("analytics/daily-summary/", auth=jwt_auth, response=List[AnalyticsDailySummaryOut], tags=["Analytics"])
def analytics_daily_summary(request, days: int = 7):
    if not is_admin(request.auth):
        raise HttpError(403, "Hanya admin yang boleh melihat ringkasan harian aktivitas")
    return get_daily_activity_summary(days=days)


@apiv1.get("courses/{id}/contents/", response=PaginatedCourseContentOut, auth=jwt_auth, tags=["Contents"])
def course_contents(request, id: int, ordering: str = "name", page: int = 1, per_page: int = 10):
    course = get_object_or_404(Course, pk=id)
    is_member = CourseMember.objects.filter(course_id=course, user_id=request.auth).exists()
    if not is_member and not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya peserta terdaftar atau owner yang bisa melihat konten course ini")
    qs = CourseContent.objects.filter(course_id=course)
    allowed_ordering = ["name", "-name", "created_at", "-created_at"]
    if ordering not in allowed_ordering:
        ordering = "name"
    qs = qs.order_by(ordering)
    total = qs.count()
    offset = (page - 1) * per_page
    results = list(qs[offset:offset + per_page])
    return {"total": total, "page": page, "per_page": per_page, "results": results}


@apiv1.post("courses/{id}/visit/", auth=jwt_auth, tags=["Courses"])
def visit_course(request, id: int):
    course = get_object_or_404(Course, pk=id)
    visited = request.session.get("visited_courses", [])
    if id not in visited:
        visited.append(id)
        request.session["visited_courses"] = visited
    log_activity(request.auth.id, request.auth.username, 'view_course', {
        'target_type': 'course', 'target_id': course.id,
        'course_name': course.name,
    })
    record_learning_analytics(request.auth.id, course.id, 'course_view', value=1)
    return {
        "course_id": id,
        "total_visited": len(visited),
        "visited_courses": visited,
    }


@apiv1.get("my-history/", auth=jwt_auth, tags=["Courses"])
def my_history(request):
    visited = request.session.get("visited_courses", [])
    return {
        "total_visited": len(visited),
        "visited_courses": visited,
    }


@apiv1.post("courses/{id}/upload-image/", auth=jwt_auth, tags=["Courses"], throttle=[UploadThrottle()])
def upload_course_image(request, id: int, file: UploadedFile = File(...)):
    course = get_object_or_404(Course, pk=id)
    if course.teacher != request.auth:
        raise HttpError(403, "Hanya teacher pemilik course yang boleh mengupload gambar.")
    if file.size > 2 * 1024 * 1024:
        raise HttpError(400, "Ukuran file maksimal 2MB.")
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HttpError(400, "Tipe file harus JPEG, PNG, atau WebP.")
    course.image = file
    course.save()
    return {"message": "Image berhasil diupload.", "filename": file.name}


@apiv1.post("courses/{id}/enroll/", response={201: dict}, auth=jwt_auth, tags=["Enrollments"])
def enroll_course_by_id(request, id: int):
    user = request.auth
    if get_user_role(user) == "instructor":
        raise HttpError(403, "Instructor tidak bisa mendaftar sebagai student")
    course = get_object_or_404(Course, pk=id)
    member, created = CourseMember.objects.get_or_create(
        course_id=course, user_id=user, defaults={"roles": "std"})
    if not created:
        raise HttpError(400, "Kamu sudah terdaftar di course ini")
    increment_course_popularity(course.id)
    log_activity(user.id, user.username, 'enroll_course', {
        'target_type': 'course', 'target_id': course.id,
        'course_name': course.name,
    })
    record_learning_analytics(user.id, course.id, 'enrollment', value=1)
    send_enrollment_email.delay(user.id, course.id)
    return 201, {"message": f"Berhasil mendaftar ke {course.name}", "enrollment_id": member.id}


@apiv1.post("enrollments/", response={201: dict}, auth=jwt_auth, tags=["Enrollments"])
def enroll_course(request, data: EnrollmentIn):
    user = request.auth
    if get_user_role(user) == "instructor":
        raise HttpError(403, "Instructor tidak bisa mendaftar sebagai student")
    course = get_object_or_404(Course, pk=data.course_id)
    member, created = CourseMember.objects.get_or_create(
        course_id=course, user_id=user, defaults={"roles": "std"})
    if not created:
        raise HttpError(400, "Kamu sudah terdaftar di course ini")
    increment_course_popularity(course.id)
    log_activity(user.id, user.username, 'enroll_course', {
        'target_type': 'course', 'target_id': course.id,
        'course_name': course.name,
    })
    record_learning_analytics(user.id, course.id, 'enrollment', value=1)
    send_enrollment_email.delay(user.id, course.id)
    return 201, {"message": f"Berhasil mendaftar ke {course.name}", "enrollment_id": member.id}


@apiv1.get("mycourses/", response=List[EnrollmentOut], auth=jwt_auth, tags=["Enrollments"])
@apiv1.get("enrollments/my-courses/", response=List[EnrollmentOut], auth=jwt_auth, tags=["Enrollments"])
def my_courses(request):
    enrollments = CourseMember.objects.filter(
        user_id=request.auth
    ).select_related("course_id", "course_id__teacher")
    result = []
    for e in enrollments:
        course = e.course_id
        result.append({
            "enrollment_id": e.id, "course_id": course.id,
            "course_name": course.name, "course_price": course.price,
            "teacher": course.teacher.get_full_name() or course.teacher.username,
            "role": e.roles,
        })
    return result


@apiv1.post("courses/{id}/request-certificate/", response={202: dict}, auth=jwt_auth, tags=["Courses"])
def request_certificate(request, id: int):
    course = get_object_or_404(Course, pk=id)
    if not CourseMember.objects.filter(course_id=course, user_id=request.auth).exists():
        raise HttpError(403, "Hanya peserta terdaftar yang dapat meminta sertifikat")
    task = generate_certificate.delay(request.auth.id, course.id)
    return 202, {"status": "queued", "task_id": task.id, "task": "generate_certificate"}


@apiv1.post("courses/{id}/export-report/", response={202: dict}, auth=jwt_auth, tags=["Courses"])
def export_course_report_endpoint(request, id: int):
    course = get_object_or_404(Course, pk=id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course yang boleh mengekspor laporan")
    task = export_course_report.delay(course.id)
    return 202, {"status": "queued", "task_id": task.id, "task": "export_course_report"}


@apiv1.post("analytics/schedule-statistics/", response={202: dict}, auth=jwt_auth, tags=["Analytics"])
def schedule_statistics(request):
    if not is_admin(request.auth):
        raise HttpError(403, "Hanya admin yang boleh menjadwalkan pembaruan statistik")
    task = update_course_statistics.delay()
    return 202, {"status": "queued", "task_id": task.id, "task": "update_course_statistics"}


@apiv1.get("tasks/{task_id}/", response=TaskStatusOut, auth=jwt_auth, tags=["Tasks"])
def task_status(request, task_id: str):
    async_result = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": async_result.status,
        "result": async_result.result if async_result.successful() else None,
        "completed": async_result.ready(),
        "failed": async_result.failed(),
        "traceback": async_result.traceback if async_result.failed() else None,
    }


@apiv1.get("contents/", response=PaginatedCourseContentOut, tags=["Contents"])
def list_contents(
    request,
    filters: ContentFilter = Query(...),
    ordering: str = "name",
    page: int = 1,
    per_page: int = 10,
):
    qs = CourseContent.objects.select_related("course_id").all()
    qs = filters.filter(qs)
    allowed_ordering = ["name", "-name", "created_at", "-created_at"]
    if ordering not in allowed_ordering:
        ordering = "name"
    qs = qs.order_by(ordering)
    total = qs.count()
    offset = (page - 1) * per_page
    results = list(qs[offset:offset + per_page])
    return {"total": total, "page": page, "per_page": per_page, "results": results}


@apiv1.post("contents/", response={201: CourseContentOut}, auth=jwt_auth, tags=["Contents"])
def create_content(request, data: CourseContentIn):
    course = get_object_or_404(Course, pk=data.course_id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course yang bisa menambah konten")
    parent = None
    if data.parent_id:
        parent = get_object_or_404(CourseContent, pk=data.parent_id)
    content = CourseContent.objects.create(
        name=data.name, description=data.description,
        video_url=data.video_url, course_id=course, parent_id=parent,
    )
    return 201, {
        "id": content.id, "name": content.name, "description": content.description,
        "video_url": content.video_url, "file_attachment": content.file_attachment.name if content.file_attachment else None,
        "course_id": content.course_id.id,
        "parent_id": content.parent_id.id if content.parent_id else None,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


@apiv1.put("contents/{id}/", response=CourseContentOut, auth=jwt_auth, tags=["Contents"])
@apiv1.patch("contents/{id}/", response=CourseContentOut, auth=jwt_auth, tags=["Contents"])
def update_content(request, id: int, data: CourseContentPatchIn):
    content = get_object_or_404(CourseContent, pk=id)
    if not is_course_owner(request.auth, content.course_id):
        raise HttpError(403, "Hanya pemilik course yang bisa mengubah konten")
    payload = data.dict(exclude_unset=True)
    for attr, value in payload.items():
        setattr(content, attr, value)
    content.save()
    return {
        "id": content.id, "name": content.name, "description": content.description,
        "video_url": content.video_url,
        "file_attachment": content.file_attachment.name if content.file_attachment else None,
        "course_id": content.course_id.id,
        "parent_id": content.parent_id.id if content.parent_id else None,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


@apiv1.post("contents/{id}/upload/", auth=jwt_auth, tags=["Contents"], throttle=[UploadThrottle()])
@apiv1.post("contents/{id}/upload-attachment/", auth=jwt_auth, tags=["Contents"], throttle=[UploadThrottle()])
def upload_content_attachment(request, id: int, file: UploadedFile = File(...)):
    content = get_object_or_404(CourseContent, pk=id)
    if content.course_id.teacher != request.auth:
        raise HttpError(403, "Hanya teacher pemilik course yang boleh mengupload attachment.")
    if file.size > 10 * 1024 * 1024:
        raise HttpError(400, "Ukuran file maksimal 10MB.")
    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/zip",
    ]
    allowed_extensions = [".pdf", ".docx", ".pptx", ".zip"]
    ext = os.path.splitext(file.name)[1].lower()
    if file.content_type not in allowed_types or ext not in allowed_extensions:
        raise HttpError(400, "Tipe file tidak diizinkan. Allowed: PDF, DOCX, PPTX, ZIP")
    content.file_attachment = file
    content.save()
    return {"message": "Attachment berhasil diupload.", "filename": file.name}


@apiv1.get("contents/{id}/download/", auth=jwt_auth, tags=["Contents"])
def download_content_attachment(request, id: int):
    content = get_object_or_404(CourseContent, pk=id)
    is_member = CourseMember.objects.filter(
        course_id=content.course_id,
        user_id=request.auth,
    ).exists()
    if not is_member and not is_course_owner(request.auth, content.course_id):
        raise HttpError(403, "Anda harus terdaftar di course ini untuk mendownload file.")
    if not content.file_attachment:
        raise HttpError(404, "Content ini tidak memiliki file attachment.")
    return FileResponse(
        content.file_attachment.open("rb"),
        as_attachment=True,
        filename=os.path.basename(content.file_attachment.name),
    )


@apiv2.get("courses/{id}", response=CourseOutV2, auth=jwt_auth, tags=["Courses"])
def detail_course_v2(request, id: int):
    try:
        course = Course.objects.select_related("teacher").annotate(
            member_count=Count("coursemember")
        ).get(pk=id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "price": course.price,
        "teacher": {
            "id": course.teacher.id,
            "username": course.teacher.username,
            "full_name": course.teacher.get_full_name(),
        },
        "member_count": course.member_count,
        "created_at": course.created_at,
    }


@apiv1.delete("contents/{id}/", response={204: None}, auth=jwt_auth, tags=["Contents"])
def delete_content(request, id: int):
    content = get_object_or_404(CourseContent, pk=id)
    if not is_course_owner(request.auth, content.course_id):
        raise HttpError(403, "Hanya pemilik course atau Admin yang bisa menghapus konten")
    content.delete()
    return 204, None


@apiv1.post("comments/", response={201: dict}, auth=jwt_auth, tags=["Comments"])
def post_comment(request, data: CommentIn):
    user = request.auth
    content = get_object_or_404(CourseContent, pk=data.content_id)
    membership = CourseMember.objects.filter(user_id=user, course_id=content.course_id).first()
    if not membership:
        raise HttpError(403, "Anda tidak terdaftar di course ini")
    comment = Comment.objects.create(
        comment=data.comment, content_id=content, member_id=membership,
    )
    return 201, {"id": comment.id, "message": "Komentar berhasil ditambahkan"}


@apiv1.put("comments/{id}/", response=dict, auth=jwt_auth, tags=["Comments"])
def update_comment(request, id: int, data: CommentUpdateIn):
    user = request.auth
    try:
        comment = Comment.objects.select_related("member_id__user_id").get(pk=id)
    except Comment.DoesNotExist:
        raise HttpError(404, "Komentar tidak ditemukan")
    if comment.member_id.user_id != user:
        raise HttpError(403, "Anda tidak memiliki izin untuk mengedit komentar ini")
    comment.comment = data.comment
    comment.save()
    return {"id": comment.id, "message": "Komentar berhasil diperbarui"}


@apiv1.delete("comments/{id}/", response={204: None}, auth=jwt_auth, tags=["Comments"])
def delete_comment(request, id: int):
    user = request.auth
    try:
        comment = Comment.objects.select_related(
            "content_id__course_id", "member_id__user_id"
        ).get(pk=id)
    except Comment.DoesNotExist:
        raise HttpError(404, "Komentar tidak ditemukan")
    is_comment_owner = (comment.member_id.user_id == user)
    is_teacher = (comment.content_id.course_id.teacher == user)
    is_superadmin = user.is_superuser
    if not (is_comment_owner or is_teacher or is_superadmin):
        raise HttpError(403, "Anda tidak memiliki izin untuk menghapus komentar ini")
    comment.delete()
    return 204, None
