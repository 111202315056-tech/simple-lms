from ninja import NinjaAPI
from ninja.errors import HttpError
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q
from django.db import IntegrityError
from typing import List, Optional
from .models import Course, CourseMember, CourseContent
from .schemas import (
    RegisterIn, LoginIn, TokenOut, RefreshIn, AccessTokenOut,
    UserOut, UserUpdateIn,
    CourseIn, CoursePatchIn, CourseOut, DetailCourseOut, PaginatedCourseOut,
    CourseContentIn, CourseContentOut, EnrollmentOut,
)
from .auth import (
    jwt_auth, create_access_token, create_refresh_token,
    decode_token, get_user_role, is_course_owner,
    is_instructor, is_admin, is_student,
)
from .helpers import get_object_or_404

apiv1 = NinjaAPI(
    title="Simple LMS API",
    version="1.0.0",
    description="REST API dengan JWT Authentication dan Role-Based Access Control",
    docs_url="/docs",
)


# ══════════════════════════════════════════════
#  AUTH ENDPOINTS
# ══════════════════════════════════════════════

@apiv1.post('auth/register', response={201: UserOut}, tags=["Auth"])
def register(request, data: RegisterIn):
    """Register user baru."""
    if User.objects.filter(username=data.username).exists():
        raise HttpError(400, "Username sudah digunakan")
    if User.objects.filter(email=data.email).exists():
        raise HttpError(400, "Email sudah digunakan")
    user = User.objects.create(
        username=data.username,
        email=data.email,
        password=make_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
    )
    return 201, {
        "id": user.id, "username": user.username,
        "email": user.email, "first_name": user.first_name,
        "last_name": user.last_name, "role": get_user_role(user),
    }


@apiv1.post('auth/login', response=TokenOut, tags=["Auth"])
def login(request, data: LoginIn):
    """Login dan dapatkan JWT token."""
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


@apiv1.post('auth/refresh', response=AccessTokenOut, tags=["Auth"])
def refresh_token(request, data: RefreshIn):
    """Refresh access token."""
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HttpError(401, "Refresh token tidak valid")
    try:
        user = User.objects.get(pk=payload["sub"])
    except User.DoesNotExist:
        raise HttpError(401, "User tidak ditemukan")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@apiv1.get('auth/me', response=UserOut, auth=jwt_auth, tags=["Auth"])
def get_me(request):
    """Dapatkan data user yang sedang login."""
    user = request.auth
    return {
        "id": user.id, "username": user.username,
        "email": user.email, "first_name": user.first_name,
        "last_name": user.last_name, "role": get_user_role(user),
    }


@apiv1.put('auth/me', response=UserOut, auth=jwt_auth, tags=["Auth"])
def update_me(request, data: UserUpdateIn):
    """Update profil user yang sedang login."""
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
        "id": user.id, "username": user.username,
        "email": user.email, "first_name": user.first_name,
        "last_name": user.last_name, "role": get_user_role(user),
    }


# ══════════════════════════════════════════════
#  COURSES - PUBLIC
# ══════════════════════════════════════════════

@apiv1.get('courses', response=PaginatedCourseOut, tags=["Courses"])
def list_courses(
    request,
    search: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    ordering: str = '-created_at',
    page: int = 1,
    per_page: int = 10,
):
    """List semua course dengan pagination dan filter (public)."""
    qs = Course.objects.select_related('teacher').all()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)
    qs = qs.order_by(ordering)
    total = qs.count()
    offset = (page - 1) * per_page
    results = list(qs[offset:offset + per_page])
    return {"total": total, "page": page, "per_page": per_page, "results": results}


@apiv1.get('courses/{id}', response=DetailCourseOut, tags=["Courses"])
def detail_course(request, id: int):
    """Detail course beserta kontennya (public)."""
    try:
        return Course.objects.select_related('teacher').prefetch_related(
            'coursecontent_set').get(pk=id)
    except Course.DoesNotExist:
        raise HttpError(404, "Course tidak ditemukan")


# ══════════════════════════════════════════════
#  COURSES - PROTECTED
# ══════════════════════════════════════════════

@apiv1.post('courses', response={201: CourseOut}, auth=jwt_auth, tags=["Courses"])
def create_course(request, data: CourseIn):
    """Buat course baru - Instructor/Admin only."""
    is_instructor(request)
    if data.price < 0:
        raise HttpError(400, "Harga tidak boleh negatif")
    course = Course.objects.create(
        name=data.name,
        description=data.description,
        price=data.price,
        teacher=request.auth,
    )
    return 201, course


@apiv1.patch('courses/{id}', response=CourseOut, auth=jwt_auth, tags=["Courses"])
def update_course(request, id: int, data: CoursePatchIn):
    """Update course - Owner/Admin only."""
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
    return course


@apiv1.delete('courses/{id}', response={204: None}, auth=jwt_auth, tags=["Courses"])
def delete_course(request, id: int):
    """Hapus course - Admin only."""
    is_admin(request)
    course = get_object_or_404(Course, pk=id)
    try:
        course.delete()
        return 204, None
    except Exception:
        raise HttpError(400, "Course tidak bisa dihapus karena masih ada relasi")


# ══════════════════════════════════════════════
#  ENROLLMENTS
# ══════════════════════════════════════════════

@apiv1.post('enrollments', response={201: dict}, auth=jwt_auth, tags=["Enrollments"])
def enroll_course(request, course_id: int):
    """Daftar ke course - Student only."""
    user = request.auth
    role = get_user_role(user)
    if role == "instructor":
        raise HttpError(403, "Instructor tidak bisa mendaftar sebagai student")
    course = get_object_or_404(Course, pk=course_id)
    member, created = CourseMember.objects.get_or_create(
        course_id=course, user_id=user, defaults={'roles': 'std'})
    if not created:
        raise HttpError(400, "Kamu sudah terdaftar di course ini")
    return 201, {
        "message": f"Berhasil mendaftar ke {course.name}",
        "enrollment_id": member.id,
    }


@apiv1.get('enrollments/my-courses', response=List[EnrollmentOut], auth=jwt_auth, tags=["Enrollments"])
def my_courses(request):
    """Lihat course yang sudah diikuti."""
    user = request.auth
    enrollments = CourseMember.objects.filter(
        user_id=user
    ).select_related('course_id', 'course_id__teacher')
    result = []
    for e in enrollments:
        course = e.course_id
        result.append({
            "enrollment_id": e.id,
            "course_id": course.id,
            "course_name": course.name,
            "course_price": course.price,
            "teacher": course.teacher.get_full_name() or course.teacher.username,
            "role": e.roles,
        })
    return result


@apiv1.post('enrollments/{id}/progress', response=dict, auth=jwt_auth, tags=["Enrollments"])
def mark_progress(request, id: int, completed: bool = True):
    """Tandai enrollment progress."""
    user = request.auth
    try:
        enrollment = CourseMember.objects.get(pk=id, user_id=user)
    except CourseMember.DoesNotExist:
        raise HttpError(404, "Enrollment tidak ditemukan")
    return {
        "message": "Progress berhasil dicatat",
        "enrollment_id": id,
        "completed": completed,
    }
