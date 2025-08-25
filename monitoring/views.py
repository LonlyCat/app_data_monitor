from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


@require_http_methods(["GET"])
@csrf_exempt
def health_check(request):
    """健康检查接口"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'app-data-monitor'
    })