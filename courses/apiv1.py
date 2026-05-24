from ninja import NinjaAPI, Schema, File, UploadedFile
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle, AuthRateThrottle
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from django.http import JsonResponse
from django.conf import settings
from typing import List, Optional
from .models import Course, CourseMember, CourseContent, Comment
from .schemas import (
    RegisterIn, LoginIn, TokenOut, RefreshIn, AccessTokenOut,
    UserOut, UserUpdateIn,
    CourseIn, CoursePatchIn, CourseOut, DetailCourseOut, PaginatedCourseOut,
    CourseContentIn, CourseContentOut, EnrollmentOut,
    CommentIn, CommentOut,
)
from .auth import (
    jwt_auth, create_access_token, create_refresh_token,
    decode_token, get_user_role, is_course_owner,
    is_instructor, is_admin, is_student,
)
from .helpers import get_object_or_404
from .cache import (
    get_course_list_cache, set_course_list_cache,
    get_course_detail_cache, set_course_detail_cache,
    invalidate_course_cache,
)
from .mongo import log_activity, log_course_view
from .tasks import send_enrollment_email, export_course_report


class CommentUpdateIn(Schema):
    comment: str


class AnonThrottle(AnonRateThrottle):
    rate = "60/minute"

class AuthThrottle(AuthRateThrottle):
    rate = "60/minute"


apiv1 = NinjaAPI(
    title="Simple LMS API",
    version="1.0.0",
    description="REST API dengan JWT Authentication dan Role-Based Access Control",
    docs_url="/docs",
    throttle=[AnonThrottle(), AuthThrottle()],
)


@apiv1.exception_handler(Ratelimited)
def ratelimited_handler(request, exc):
    return JsonResponse({"detail": "Terlalu banyak request. Coba lagi nanti."}, status=429)


@apiv1.post("auth/register", response={201: UserOut}, tags=["Auth"])
def register(request, data: RegisterIn):
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah digunakan")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah digunakan")
    user = User.objects.create(
        username=data.username, email=data.email,
        password=make_password(data.password),
        first_name=data.first_name, last_name=data.last_name,
    )
    return 201, {
        "id": user.id, "username": user.username, "email": user.email,
        "first_name": user.first_name, "last_name": user.last_name,
        "role": get_user_role(user),
    }


@apiv1.post("auth/login", response=TokenOut, tags=["Auth"])
@ratelimit(key="ip", rate="5/m", method="POST", block=True)
def login(request, data: LoginIn):
    try:
        user = User.objects.get(username=data.username)
    except User.DoesNotExist:
        raise HttpError(401, "Username atau password salah")
    if not check_password(data.password, user.password):
        raise HttpError(401, "Username atau password salah")
    log_activity(user.id, "login", {"username": user.username})
    return {
        "access_token": create_access_token(user.id),
        "refresh_token": create_refresh_token(user.id),
        "token_type": "bearer",
    }


@apiv1.post("auth/refresh", response=AccessTokenOut, tags=["Auth"])
def refresh_token(request, data: RefreshIn):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HttpError(401, "Refresh token tidak valid")
    try:
        user = User.objects.get(pk=payload["sub"])
    except User.DoesNotExist:
        raise HttpError(401, "User tidak ditemukan")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@apiv1.get("auth/me", response=UserOut, auth=jwt_auth, tags=["Auth"])
def get_me(request):
    user = request.auth
    return {
        "id": user.id, "username": user.username, "email": user.email,
        "first_name": user.first_name, "last_name": user.last_name,
        "role": get_user_role(user),
    }


@apiv1.put("auth/me", response=UserOut, auth=jwt_auth, tags=["Auth"])
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


@apiv1.get("courses", response=PaginatedCourseOut, tags=["Courses"])
def list_courses(
    request,
    search: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    ordering: str = "-created_at",
    page: int = 1,
    per_page: int = 10,
):
    # Cek cache dulu
    cached = get_course_list_cache(page, per_page, search, ordering)
    if cached:
        return cached

    qs = Course.objects.select_related("teacher").all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    allowed_ordering = ["name", "-name", "price", "-price", "created_at", "-created_at"]
    if ordering not in allowed_ordering:
        ordering = "-created_at"
    qs = qs.order_by(ordering)
    total = qs.count()
    offset = (page - 1) * per_page
    results = list(qs[offset:offset + per_page])
    data = {"total": total, "page": page, "per_page": per_page, "results": results}

    # Simpan ke cache
    set_course_list_cache(page, per_page, search, ordering, data)
    return data


@apiv1.get("courses/{id}", response=DetailCourseOut, tags=["Courses"])
def detail_course(request, id: int):
    # Cek cache dulu
    cached = get_course_detail_cache(id)
    if cached:
        return cached

    try:
        course = Course.objects.select_related("teacher").prefetch_related("coursecontent_set").get(pk=id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")

    # Log view ke MongoDB
    user_id = request.auth.id if hasattr(request, "auth") and request.auth else None
    log_course_view(user_id, course.id, course.name)

    # Simpan ke cache
    set_course_detail_cache(id, course)
    return course


@apiv1.post("courses", response={201: CourseOut}, auth=jwt_auth, tags=["Courses"])
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


@apiv1.patch("courses/{id}", response=CourseOut, auth=jwt_auth, tags=["Courses"])
def update_course(request, id: int, data: CoursePatchIn):
    course = get_object_or_404(Course, pk=id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course atau Admin yang bisa mengubah")
    if data.name is not None:
        course.name = data.name
    if data.description is not None:
        course.description = data.description
    if data.price is not None:
        if data.price < 0:
            raise HttpError(400, "Harga tidak boleh negatif")
        course.price = data.price
    course.save()
    invalidate_course_cache(id)
    return course


@apiv1.delete("courses/{id}", response={204: None}, auth=jwt_auth, tags=["Courses"])
def delete_course(request, id: int):
    course = get_object_or_404(Course, pk=id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course atau Admin yang bisa menghapus")
    course.delete()
    invalidate_course_cache(id)
    return 204, None


@apiv1.post("courses/{id}/image", response=CourseOut, auth=jwt_auth, tags=["Courses"])
def upload_course_image(request, id: int, image: UploadedFile = File(...)):
    course = get_object_or_404(Course, pk=id)
    if not is_course_owner(request.auth, course):
        raise HttpError(403, "Hanya pemilik course yang bisa upload gambar")
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if image.content_type not in allowed_types:
        raise HttpError(400, "Format gambar tidak didukung. Gunakan JPG, PNG, atau WebP")
    if image.size > 2 * 1024 * 1024:
        raise HttpError(400, "Ukuran gambar maksimal 2MB")
    course.image.save(image.name, image, save=True)
    invalidate_course_cache(id)
    return course


@apiv1.post("enrollments", response={201: dict}, auth=jwt_auth, tags=["Enrollments"])
def enroll_course(request, course_id: int):
    user = request.auth
    if get_user_role(user) == "instructor":
        raise HttpError(403, "Instructor tidak bisa mendaftar sebagai student")
    course = get_object_or_404(Course, pk=course_id)
    member, created = CourseMember.objects.get_or_create(
        course_id=course, user_id=user, defaults={"roles": "std"})
    if not created:
        raise HttpError(400, "Kamu sudah terdaftar di course ini")
    # Trigger async task
    send_enrollment_email.delay(user.id, course.id)
    log_activity(user.id, "enrollment", {"course_id": course.id, "course_name": course.name})
    return 201, {"message": f"Berhasil mendaftar ke {course.name}", "enrollment_id": member.id}


@apiv1.get("enrollments/my-courses", response=List[EnrollmentOut], auth=jwt_auth, tags=["Enrollments"])
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


@apiv1.post("contents", response={201: CourseContentOut}, auth=jwt_auth, tags=["Contents"])
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
        "video_url": content.video_url, "course_id": content.course_id.id,
        "parent_id": content.parent_id.id if content.parent_id else None,
    }


@apiv1.patch("contents/{id}", response=CourseContentOut, auth=jwt_auth, tags=["Contents"])
def update_content(request, id: int, data: CoursePatchIn):
    content = get_object_or_404(CourseContent, pk=id)
    if not is_course_owner(request.auth, content.course_id):
        raise HttpError(403, "Hanya pemilik course yang bisa mengubah konten")
    if data.name is not None:
        content.name = data.name
    if data.description is not None:
        content.description = data.description
    content.save()
    return {
        "id": content.id, "name": content.name, "description": content.description,
        "video_url": content.video_url, "course_id": content.course_id.id,
        "parent_id": content.parent_id.id if content.parent_id else None,
    }


@apiv1.delete("contents/{id}", response={204: None}, auth=jwt_auth, tags=["Contents"])
def delete_content(request, id: int):
    content = get_object_or_404(CourseContent, pk=id)
    if not is_course_owner(request.auth, content.course_id):
        raise HttpError(403, "Hanya pemilik course atau Admin yang bisa menghapus konten")
    content.delete()
    return 204, None


@apiv1.post("comments", response={201: dict}, auth=jwt_auth, tags=["Comments"])
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


@apiv1.put("comments/{id}", response=dict, auth=jwt_auth, tags=["Comments"])
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


@apiv1.delete("comments/{id}", response={204: None}, auth=jwt_auth, tags=["Comments"])
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


@apiv1.post("reports/export", response=dict, auth=jwt_auth, tags=["Reports"])
def trigger_export(request, course_id: int = None):
    task = export_course_report.delay(course_id)
    return {"task_id": task.id, "status": "processing", "message": "Report sedang dibuat secara async"}


@apiv1.get("analytics/popular-courses", response=list, tags=["Analytics"])
def popular_courses(request):
    from .mongo import get_popular_courses
    return get_popular_courses(limit=10)
