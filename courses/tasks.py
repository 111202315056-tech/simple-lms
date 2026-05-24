import csv
import io
from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone


@shared_task(bind=True, max_retries=3)
def send_enrollment_email(self, user_id, course_id):
    """Kirim email saat student enroll ke course"""
    try:
        from courses.models import Course
        user = User.objects.get(pk=user_id)
        course = Course.objects.get(pk=course_id)

        # Simulate sending email (print untuk development)
        print(f"[EMAIL] Sending enrollment email to {user.email}")
        print(f"[EMAIL] Subject: Selamat! Kamu berhasil mendaftar ke {course.name}")
        print(f"[EMAIL] Dear {user.get_full_name() or user.username},")
        print(f"[EMAIL] Kamu telah berhasil mendaftar ke course: {course.name}")

        # Log ke MongoDB
        from courses.mongo import log_activity
        log_activity(
            user_id=user_id,
            action="enrollment_email_sent",
            details={"course_id": course_id, "course_name": course.name}
        )

        return {"status": "success", "user": user.username, "course": course.name}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_certificate(self, user_id, course_id):
    """Generate certificate saat course complete"""
    try:
        from courses.models import Course, CourseMember
        user = User.objects.get(pk=user_id)
        course = Course.objects.get(pk=course_id)

        # Simulate certificate generation
        cert_data = {
            "certificate_id": f"CERT-{user_id}-{course_id}-{timezone.now().strftime('%Y%m%d')}",
            "user": user.get_full_name() or user.username,
            "course": course.name,
            "issued_at": timezone.now().isoformat(),
            "status": "generated"
        }

        print(f"[CERT] Certificate generated: {cert_data['certificate_id']}")

        # Log ke MongoDB
        from courses.mongo import log_activity
        log_activity(
            user_id=user_id,
            action="certificate_generated",
            details=cert_data
        )

        return cert_data
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task
def update_course_statistics():
    """Update enrollment count untuk semua courses (scheduled task)"""
    from courses.models import Course, CourseMember
    from django.db.models import Count

    courses = Course.objects.annotate(
        enrollment_count=Count('coursemember')
    )

    stats = []
    for course in courses:
        stats.append({
            "course_id": course.id,
            "course_name": course.name,
            "enrollment_count": course.enrollment_count,
            "updated_at": timezone.now().isoformat()
        })

    # Log ke MongoDB
    from courses.mongo import get_mongo_db
    db = get_mongo_db()
    if db is not None:
        db.course_statistics.delete_many({})
        if stats:
            db.course_statistics.insert_many(stats)

    print(f"[STATS] Updated statistics for {len(stats)} courses")
    return {"updated": len(stats), "stats": stats}


@shared_task
def export_course_report(course_id=None):
    """Generate CSV report untuk courses (async)"""
    from courses.models import Course, CourseMember

    if course_id:
        courses = Course.objects.filter(pk=course_id)
    else:
        courses = Course.objects.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Price', 'Teacher', 'Enrollments', 'Created At'])

    from django.db.models import Count
    courses = courses.select_related('teacher').annotate(
        enrollment_count=Count('coursemember')
    )

    for course in courses:
        writer.writerow([
            course.id,
            course.name,
            course.price,
            course.teacher.username,
            course.enrollment_count,
            course.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])

    csv_content = output.getvalue()
    print(f"[REPORT] Generated CSV report with {courses.count()} courses")

    # Log ke MongoDB
    from courses.mongo import log_activity
    log_activity(
        user_id=None,
        action="report_generated",
        details={"course_id": course_id, "rows": courses.count()}
    )

    return {"status": "success", "csv": csv_content, "rows": courses.count()}
