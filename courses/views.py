import time
from django.http import JsonResponse
from django.db import connection, reset_queries
from django.conf import settings
from django.db.models import Count, Avg, Max, Min, Q
from .models import Course, CourseMember, CourseContent, Comment


def index(request):
    return JsonResponse({'message': 'Simple LMS API', 'status': 'ok'})


def course_list(request):
    """N+1 Problem - BAD"""
    settings.DEBUG = True
    reset_queries()
    start = time.time()

    courses = Course.objects.all()
    data = []
    for course in courses:
        data.append({
            'name': course.name,
            'price': course.price,
            'teacher': course.teacher.username,
            'member_count': CourseMember.objects.filter(course_id=course).count(),
        })

    elapsed = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)

    return JsonResponse({
        'method': 'TANPA OPTIMASI (N+1)',
        'query_count': query_count,
        'time_ms': elapsed,
        'total_courses': len(data),
        'data': data,
    })


def course_list_optimized(request):
    """Optimized - GOOD"""
    settings.DEBUG = True
    reset_queries()
    start = time.time()

    courses = Course.objects.select_related(
        'teacher'
    ).annotate(
        member_count=Count('coursemember')
    ).all()

    data = []
    for course in courses:
        data.append({
            'name': course.name,
            'price': course.price,
            'teacher': course.teacher.username,
            'member_count': course.member_count,
        })

    elapsed = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)

    return JsonResponse({
        'method': 'DENGAN OPTIMASI (select_related + annotate)',
        'query_count': query_count,
        'time_ms': elapsed,
        'total_courses': len(data),
        'data': data,
    })


def course_stats(request):
    """Aggregate & Annotate"""
    settings.DEBUG = True
    reset_queries()
    start = time.time()

    stats = Course.objects.aggregate(
        total_courses=Count('id'),
        avg_price=Avg('price'),
        max_price=Max('price'),
        min_price=Min('price'),
    )

    top5 = Course.objects.select_related('teacher').annotate(
        member_count=Count('coursemember'),
        content_count=Count('coursecontent'),
        student_count=Count('coursemember', filter=Q(coursemember__roles='std')),
        assistant_count=Count('coursemember', filter=Q(coursemember__roles='ast')),
    ).order_by('-member_count')[:5]

    elapsed = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)

    return JsonResponse({
        'query_count': query_count,
        'time_ms': elapsed,
        'stats': stats,
        'top5_popular': [
            {
                'name': c.name,
                'teacher': c.teacher.username,
                'members': c.member_count,
                'contents': c.content_count,
                'students': c.student_count,
                'assistants': c.assistant_count,
            } for c in top5
        ],
    })


def dashboard(request):
    """Dashboard N+1 - BAD"""
    settings.DEBUG = True
    reset_queries()
    start = time.time()

    courses = Course.objects.all()
    result = []
    for course in courses:
        members = CourseMember.objects.filter(course_id=course)
        contents = CourseContent.objects.filter(course_id=course)
        comment_count = 0
        for content in contents:
            comment_count += Comment.objects.filter(content_id=content).count()
        result.append({
            'course': course.name,
            'teacher': course.teacher.username,
            'members': members.count(),
            'contents': contents.count(),
            'comments': comment_count,
        })

    elapsed = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)

    return JsonResponse({
        'method': 'DASHBOARD TANPA OPTIMASI',
        'query_count': query_count,
        'time_ms': elapsed,
        'data': result,
    })


def dashboard_optimized(request):
    """Dashboard Optimized - GOOD"""
    settings.DEBUG = True
    reset_queries()
    start = time.time()

    courses = Course.objects.select_related('teacher').annotate(
        member_count=Count('coursemember', distinct=True),
        content_count=Count('coursecontent', distinct=True),
        comment_count=Count('coursecontent__comment', distinct=True),
    ).all()

    result = []
    for course in courses:
        result.append({
            'course': course.name,
            'teacher': course.teacher.username,
            'members': course.member_count,
            'contents': course.content_count,
            'comments': course.comment_count,
        })

    elapsed = round((time.time() - start) * 1000, 2)
    query_count = len(connection.queries)

    return JsonResponse({
        'method': 'DASHBOARD DENGAN OPTIMASI',
        'query_count': query_count,
        'time_ms': elapsed,
        'data': result,
    })
