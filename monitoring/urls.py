from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

app_name = 'monitoring'

urlpatterns = [
    path('', include(router.urls)),
    path('health/', views.health_check, name='health_check'),
]