"""
监控应用的URL配置
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('status/', views.api_status, name='api_status'),
]
