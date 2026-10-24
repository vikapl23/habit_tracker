from django.http import JsonResponse


class HealthCheckMiddleware:
    """Middleware that intercepts /health/ and returns 200 OK immediately.

    This bypasses SecurityMiddleware (SSL redirect) and host header validation
    (ALLOWED_HOSTS), which is required for platforms like Render whose internal
    health checks query http://localhost:10000/health/.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/":
            return JsonResponse({"status": "ok"})
        return self.get_response(request)
