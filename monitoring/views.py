"""
监控应用的视图
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.core.cache import cache
import json


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    健康检查端点
    """
    try:
        # 检查数据库连接
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # 检查缓存
    try:
        cache.set("health_check", "ok", 10)
        cache_status = "healthy" if cache.get("health_check") == "ok" else "unhealthy"
    except Exception as e:
        cache_status = f"unhealthy: {str(e)}"
    
    response_data = {
        "status": "ok",
        "database": db_status,
        "cache": cache_status,
        "timestamp": "2025-01-28T10:00:00Z"
    }
    
    return JsonResponse(response_data, status=200)


@csrf_exempt
@require_http_methods(["GET"])
def api_status(request):
    """
    API状态端点
    """
    response_data = {
        "service": "App数据监控系统",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health/",
            "admin": "/admin/",
        }
    }
    
    return JsonResponse(response_data, status=200)
