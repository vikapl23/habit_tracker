from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.coach.models import ChatMessage, PendingAction
from apps.coach.serializers import (
    ChatMessageSerializer,
    CoachMessageInputSerializer,
)
from apps.coach.services.actions import default_action_registry
from apps.coach.services.client import (
    CoachUnavailableError,
    CoachUpstreamError,
    GeminiCoachService,
    get_remaining_daily_quota,
)

logger = logging.getLogger(__name__)


class CoachMessagesView(APIView):
    """
    Coach messages conversation endpoint:
    - GET: Retrieve conversation history and remaining message quota
    - POST: Send a message to the AI habit coach
    - DELETE: Clear conversation history and cancel pending actions
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List coach conversation history and remaining quota",
        responses={200: ChatMessageSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        remaining = get_remaining_daily_quota(request.user)
        daily_limit = getattr(settings, "COACH_DAILY_MESSAGE_LIMIT", 20)
        messages = (
            ChatMessage.objects.filter(user=request.user)
            .select_related("pending_action")
            .order_by("created_at")
        )
        data = ChatMessageSerializer(messages, many=True).data
        return Response(
            {
                "remaining_messages": remaining,
                "daily_limit": daily_limit,
                "results": data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Send a message to the AI habit coach",
        request=CoachMessageInputSerializer,
        responses={201: ChatMessageSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CoachMessageInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content = serializer.validated_data["content"]

        remaining = get_remaining_daily_quota(request.user)
        if remaining <= 0:
            return Response(
                {
                    "detail": "Daily message limit reached (20/20). Your quota resets at midnight.",
                    "remaining_messages": 0,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        coach_service = GeminiCoachService()
        if not coach_service.is_configured():
            return Response(
                {
                    "detail": "AI Habit Coach is not configured or currently unavailable.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            assistant_reply, pending_action = coach_service.generate_reply(request.user, content)
        except CoachUnavailableError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except CoachUpstreamError:
            return Response(
                {
                    "detail": "AI Coach service is temporarily unavailable. Please try again shortly.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.error("Unexpected error in coach view: %s", e)
            return Response(
                {
                    "detail": "AI Coach service is temporarily unavailable. Please try again shortly.",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with transaction.atomic():
            user_msg = ChatMessage.objects.create(
                user=request.user,
                role=ChatMessage.ROLE_USER,
                content=content,
            )
            assistant_msg = ChatMessage.objects.create(
                user=request.user,
                role=ChatMessage.ROLE_ASSISTANT,
                content=assistant_reply,
                pending_action=pending_action,
            )

        new_remaining = get_remaining_daily_quota(request.user)

        return Response(
            {
                "user_message": ChatMessageSerializer(user_msg).data,
                "assistant_message": ChatMessageSerializer(assistant_msg).data,
                "remaining_messages": new_remaining,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Clear coach conversation history",
        responses={204: None},
    )
    def delete(self, request: Request) -> Response:
        with transaction.atomic():
            ChatMessage.objects.filter(user=request.user).delete()
            PendingAction.objects.filter(
                user=request.user,
                status=PendingAction.STATUS_PENDING,
            ).update(status=PendingAction.STATUS_CANCELLED)

        return Response(status=status.HTTP_204_NO_CONTENT)


class CoachActionConfirmView(APIView):
    """
    Confirm and execute a pending coach action.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Confirm and execute a pending coach action",
        responses={200: None},
    )
    def post(self, request: Request, pk: int) -> Response:
        action = get_object_or_404(PendingAction, id=pk, user=request.user)

        if action.status != PendingAction.STATUS_PENDING:
            return Response(
                {"detail": f"Action cannot be confirmed because it is {action.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action.is_expired():
            action.status = PendingAction.STATUS_EXPIRED
            action.save(update_fields=["status"])
            return Response(
                {"detail": "This action has expired (15 minute validity window)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        handler = default_action_registry.get(action.action_type)
        if not handler:
            return Response(
                {"detail": f"Unknown action type: {action.action_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            result = handler.execute(request.user, action.payload)
            action.status = PendingAction.STATUS_CONFIRMED
            action.executed_at = timezone.now()
            action.save(update_fields=["status", "executed_at"])

        return Response(
            {
                "status": "confirmed",
                "action_id": action.id,
                "action_type": action.action_type,
                "result": result,
            },
            status=status.HTTP_200_OK,
        )


class CoachActionCancelView(APIView):
    """
    Cancel a pending coach action.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Cancel a pending coach action",
        responses={200: None},
    )
    def post(self, request: Request, pk: int) -> Response:
        action = get_object_or_404(PendingAction, id=pk, user=request.user)

        if action.status != PendingAction.STATUS_PENDING:
            return Response(
                {"detail": f"Action cannot be cancelled because it is {action.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action.status = PendingAction.STATUS_CANCELLED
        action.save(update_fields=["status"])

        return Response(
            {
                "status": "cancelled",
                "action_id": action.id,
            },
            status=status.HTTP_200_OK,
        )
