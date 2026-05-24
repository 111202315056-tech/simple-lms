import time
from django.http import JsonResponse
from django.db import connection, reset_queries
from django.conf import settings
from django.db.models import Count, Avg, Max, Min, Prefetch
from .models import Course, CourseMember, CourseContent, Comment


def _reset():
    settings.DEBUG = True
    reset_queries()
    return time.time()

def _stats(start):
    return round((time.time() - start) * 1000, 2), len(connection.queries)


# ── course-list ──────────────────────────────────────────────

def course_list_baseline(request):
    start = _reset()
    courses = Course.objects.all()
    data = []
    for c in courses:
        data.append({
            'name': c.name,
            'teacher': c.teacher.username,
            'members': CourseMember.objects.filter(course_id=c).count(),
        })
    ms, qc = _stats(start)
    return JsonResponse({'method': 'course-list BASELINE (N+1)', 'query_count': qc, 'time_ms': ms, 'total': len(data), 'data': data})


def course_list_optimized(request):
    start = _reset()
    courses = Course.objects.select_related('teacher').annotate(
        member_count=Count('coursemember')
    )
    data = [{'name': c.name, 'teacher': c.teacher.username, 'members': c.member_count} for c in courses]
    ms, qc = _stats(start)
    return JsonResponse({'method': 'course-list OPTIMIZED', 'query_count': qc, 'time_ms': ms, 'total': len(data), 'data': data})


# ── course-members ───────────────────────────────────────────

def course_members_baseline(request):
    start = _reset()
    data = []
    for c in Course.objects.all():
        members = CourseMember.objects.filter(course_id=c).select_related('user_id')
        data.append({
            'course': c.name,
            'members': [m.user_id.username for m in members],
        })
    ms, qc = _stats(start)
    return JsonResponse({'method': 'course-members BASELINE (N+1)', 'query_count': qc, 'time_ms': ms, 'total': len(data), 'data': data})


def course_members_optimized(request):
    start = _reset()
    courses = Course.objects.prefetch_related(
        Prefetch('coursemember_set', queryset=CourseMember.objects.select_related('user_id'))
    )
    data = []
    for c in courses:
        data.append({
            'course': c.name,
            'members': [m.user_id.username for m in c.coursemember_set.all()],
        })
    ms, qc = _stats(start)
    return JsonResponse({'method': 'course-members OPTIMIZED (prefetch_related)', 'query_count': qc, 'time_ms': ms, 'total': len(data), 'data': data})


# ── course-dashboard ─────────────────────────────────────────

def course_dashboard_baseline(request):
    start = _reset()
    result = []
    for c in Course.objects.all():
        members = CourseMember.objects.filter(course_id=c).count()
        contents = CourseContent.objects.filter(course_id=c)
        comments = sum(Comment.objects.filter(content_id=ct).count() for ct in contents)
        result.append({'course': c.name, 'teacher': c.teacher.username, 'members': members, 'contents': contents.count(), 'comments': comments})
    ms, qc = _stats(start)
    return JsonResponse({'method': 'course-dashboard BASELINE (N+1)', 'query_count': qc, 'time_ms': ms, 'data': result})


def course_dashboard_optimized(request):
    start = _reset()
    courses = Course.objects.select_related('teacher').annotate(
        member_count=Count('coursemember', distinct=True),
        content_count=Count('coursecontent', distinct=True),
        comment_count=Count('coursecontent__comment', distinct=True),
    )
    result = [{'course': c.name, 'teacher': c.teacher.username, 'members': c.member_count, 'contents': c.content_count, 'comments': c.comment_count} for c in courses]
    ms, qc = _stats(start)
    return JsonResponse({'method': 'course-dashboard OPTIMIZED', 'query_count': qc, 'time_ms': ms, 'data': result})


# ── bulk-demo ────────────────────────────────────────────────

def bulk_demo(request):
    start = _reset()

    # bulk_create
    new_courses = [Course(name=f'Bulk Course {i}', price=i*1000, teacher_id=1, description='bulk') for i in range(1, 6)]
    Course.objects.bulk_create(new_courses, ignore_conflicts=True)

    # bulk_update
    to_update = list(Course.objects.filter(name__startswith='Bulk Course')[:5])
    for c in to_update:
        c.price = 99999
    Course.objects.bulk_update(to_update, ['price'])

    ms, qc = _stats(start)
    return JsonResponse({'method': 'bulk_create + bulk_update', 'query_count': qc, 'time_ms': ms, 'bulk_created': len(new_courses), 'bulk_updated': len(to_update)})
