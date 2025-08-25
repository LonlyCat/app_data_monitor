"""
URL configuration for app_monitor project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
]

admin.site.site_header = "App数据监控管理后台"
admin.site.site_title = "App监控系统"
admin.site.index_title = "欢迎使用App数据监控平台"