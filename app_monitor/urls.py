"""
URL configuration for app_monitor project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    # 将根路径重定向到管理后台，避免直接访问 / 出现 404
    path('', RedirectView.as_view(url='/admin/', permanent=False), name='root'),
    path('admin/', admin.site.urls),
    path('api/', include('monitoring.urls')),
]

admin.site.site_header = "App数据监控管理后台"
admin.site.site_title = "App监控系统"
admin.site.index_title = "欢迎使用App数据监控平台"
