from ninja import Schema, Field
from datetime import datetime
from typing import Optional, List


class RegisterIn(Schema):
    username: str
    email: str
    password: str
    first_name: str = ''
    last_name: str = ''


class LoginIn(Schema):
    username: str
    password: str


class TokenOut(Schema):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class RefreshIn(Schema):
    refresh_token: str


class AccessTokenOut(Schema):
    access_token: str
    token_type: str = 'bearer'


class UserOut(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: str


class UserUpdateIn(Schema):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None


class TeacherOut(Schema):
    id: int
    username: str
    first_name: str
    last_name: str


class CourseIn(Schema):
    name: str
    description: str = '-'
    price: int = 0


class CoursePatchIn(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None


class CourseOut(Schema):
    id: int
    name: str
    description: str
    price: int
    image: Optional[str] = ''
    teacher: TeacherOut
    created_at: datetime
    updated_at: datetime


class ContentTitleOut(Schema):
    id: int
    name: str


class DetailCourseOut(CourseOut):
    contents: List[ContentTitleOut] = Field(
        ..., alias="coursecontent_set"
    )


class PaginatedCourseOut(Schema):
    total: int
    page: int
    per_page: int
    results: List[CourseOut]


class CourseContentIn(Schema):
    name: str
    description: str = '-'
    video_url: Optional[str] = None
    course_id: int
    parent_id: Optional[int] = None


class CourseContentOut(Schema):
    id: int
    name: str
    description: str
    video_url: Optional[str] = None
    course_id: int
    parent_id: Optional[int] = None


class EnrollmentOut(Schema):
    enrollment_id: int
    course_id: int
    course_name: str
    course_price: int
    teacher: str
    role: str
