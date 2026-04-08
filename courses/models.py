from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Prefetch


# ── 1. USER dengan ROLE ──────────────────────────────────
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


# ── 2. CATEGORY (self-referencing) ──────────────────────
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='children'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


# ── 3. COURSE MANAGER ───────────────────────────────────
class CourseQuerySet(models.QuerySet):
    def for_listing(self):
        return self.select_related('instructor', 'category').annotate(
            enrollment_count=models.Count('enrollments')
        ).filter(is_published=True)


class CourseManager(models.Manager):
    def get_queryset(self):
        return CourseQuerySet(self.model, using=self._db)

    def for_listing(self):
        return self.get_queryset().for_listing()


# ── 4. COURSE ────────────────────────────────────────────
class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(default='-')
    instructor = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='courses_taught',
        limit_choices_to={'role': 'instructor'}
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='courses'
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CourseManager()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"


# ── 5. LESSON (dengan ordering) ──────────────────────────
class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    title = models.CharField(max_length=200)
    content = models.TextField(default='-')
    video_url = models.URLField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.order}. {self.title}"

    class Meta:
        ordering = ['order']
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"


# ── 6. ENROLLMENT MANAGER ───────────────────────────────
class EnrollmentQuerySet(models.QuerySet):
    def for_student_dashboard(self, user):
        return self.filter(student=user).select_related(
            'course', 'course__instructor', 'course__category'
        ).prefetch_related(
            Prefetch(
                'course__lessons',
                queryset=Lesson.objects.order_by('order')
            ),
            'progresses'
        )


class EnrollmentManager(models.Manager):
    def get_queryset(self):
        return EnrollmentQuerySet(self.model, using=self._db)

    def for_student_dashboard(self, user):
        return self.get_queryset().for_student_dashboard(user)


# ── 7. ENROLLMENT (unique constraint) ───────────────────
class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'student'}
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    objects = EnrollmentManager()

    def __str__(self):
        return f"{self.student.username} -> {self.course.title}"

    class Meta:
        unique_together = ('student', 'course')
        verbose_name = "Enrollment"
        verbose_name_plural = "Enrollments"


# ── 8. PROGRESS (tracking lesson completion) ─────────────
class Progress(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='progresses'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progresses'
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = "✅" if self.is_completed else "⬜"
        return f"{status} {self.enrollment.student.username} - {self.lesson.title}"

    class Meta:
        unique_together = ('enrollment', 'lesson')
        verbose_name = "Progress"
        verbose_name_plural = "Progresses"
