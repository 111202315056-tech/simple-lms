from django.contrib import admin
from django.urls import path, include
from courses.apiv1 import apiv1

urlpatterns = [
    path('admin/', admin.site.urls),
    path('silk/', include('silk.urls', namespace='silk')),
    path('api/', apiv1.urls),
]
