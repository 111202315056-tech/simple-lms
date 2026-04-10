from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/optimized/', views.course_list_optimized, name='course_list_optimized'),
    path('courses/stats/', views.course_stats, name='course_stats'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/optimized/', views.dashboard_optimized, name='dashboard_optimized'),
]
