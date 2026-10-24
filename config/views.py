from django.http import JsonResponse


def healthcheck_view(request):
    """Simple healthcheck endpoint returning status ok."""
    return JsonResponse({"status": "ok"})
