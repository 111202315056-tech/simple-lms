import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from ninja.security import HttpBearer
from ninja.errors import HttpError
from django.contrib.auth.models import User
from django.conf import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def get_user_role(user: User) -> str:
    if user.is_superuser:
        return "admin"
    if user.is_staff:
        return "instructor"
    return "student"


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HttpError(401, "Token sudah kadaluarsa")
    except jwt.InvalidTokenError:
        raise HttpError(401, "Token tidak valid")


def is_course_owner(user: User, course) -> bool:
    return course.teacher == user or user.is_superuser


class JWTAuth(HttpBearer):
    def authenticate(self, request, token: str):
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HttpError(401, "Token tidak valid")
        try:
            user = User.objects.get(pk=payload["sub"])
            request.user = user
            return user
        except User.DoesNotExist:
            raise HttpError(401, "User tidak ditemukan")


jwt_auth = JWTAuth()


def is_instructor(request):
    user = request.auth
    role = get_user_role(user)
    if role not in ["instructor", "admin"]:
        raise HttpError(403, "Hanya Instructor atau Admin yang diizinkan")
    return user


def is_admin(request):
    user = request.auth
    if not user.is_superuser:
        raise HttpError(403, "Hanya Admin yang diizinkan")
    return user


def is_student(request):
    user = request.auth
    role = get_user_role(user)
    if role != "student":
        raise HttpError(403, "Hanya Student yang diizinkan")
    return user
