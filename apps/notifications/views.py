from __future__ import annotations

import secrets
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.services import send_due_notifications
from apps.notifications.tokens import verify_unsubscribe_token

User = get_user_model()


class SendNotificationsInternalView(APIView):
    """
    Protected internal endpoint to trigger due notification dispatching via cron.
    Authorized via constant-time comparison of X-Cron-Token header.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        cron_token = getattr(settings, "CRON_TOKEN", "") or ""
        header_token = request.headers.get("X-Cron-Token", "")

        if not cron_token:
            return Response(
                {"detail": "Cron token is not configured on the server."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not header_token or not secrets.compare_digest(header_token, cron_token):
            return Response(
                {"detail": "Invalid or missing cron authorization token."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Allow passing force in JSON body or query param
        force = False
        if isinstance(request.data, dict) and "force" in request.data:
            force = bool(request.data["force"])
        elif "force" in request.query_params:
            force = request.query_params.get("force", "").lower() in ("true", "1")

        counts = send_due_notifications(force=force)
        return Response(
            {
                "status": "success",
                **counts,
            },
            status=status.HTTP_200_OK,
        )


class UnsubscribeView(APIView):
    """
    Public one-click unsubscribe endpoint allowing users to opt out of
    all email notifications via a signed token without logging in.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request: Request, token: str, *args: Any, **kwargs: Any) -> Response:
        return self._process_unsubscribe(token)

    def post(self, request: Request, token: str, *args: Any, **kwargs: Any) -> Response:
        return self._process_unsubscribe(token)

    def _process_unsubscribe(self, token: str) -> Response:
        user_id = verify_unsubscribe_token(token)
        if not user_id:
            return Response(
                {"detail": "Invalid or expired unsubscribe link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user.notifications_enabled = False
        user.save(update_fields=["notifications_enabled"])

        return Response(
            {
                "detail": "You have been successfully unsubscribed from all email notifications.",
                "unsubscribed": True,
            },
            status=status.HTTP_200_OK,
        )
