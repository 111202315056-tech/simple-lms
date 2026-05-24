from django.urls import path
from . import views
from . import lab_views

urlpatterns = [
    path('', views.index, name='index'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/optimized/', views.course_list_optimized, name='course_list_optimized'),
    path('courses/stats/', views.course_stats, name='course_stats'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/optimized/', views.dashboard_optimized, name='dashboard_optimized'),

    # Lab URLs (Modul 5)
    path('lab/course-list/baseline/', lab_views.course_list_baseline, name='lab_course_list_baseline'),
    path('lab/course-list/optimized/', lab_views.course_list_optimized, name='lab_course_list_optimized'),
    path('lab/course-members/baseline/', lab_views.course_members_baseline, name='lab_course_members_baseline'),
    path('lab/course-members/optimized/', lab_views.course_members_optimized, name='lab_course_members_optimized'),
    path('lab/course-dashboard/baseline/', lab_views.course_dashboard_baseline, name='lab_course_dashboard_baseline'),
    path('lab/course-dashboard/optimized/', lab_views.course_dashboard_optimized, name='lab_course_dashboard_optimized'),
    path('lab/bulk-demo/', lab_views.bulk_demo, name='lab_bulk_demo'),
]
