from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Habit
from .serializers import (
    ArchiveResponseSerializer,
    CheckInActionSerializer,
    CheckInFilterSerializer,
    CheckInResponseSerializer,
    HabitCheckInSerializer,
    HabitSerializer,
)
from .services import CheckInResult, check_in_habit, uncheck_habit


class HabitViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user habits, streak tracking, and check-in history."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = HabitSerializer

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        """Validate query parameters on request initialization."""
        super().initial(request, *args, **kwargs)
        if "date" in request.query_params:
            date_param = request.query_params.get("date")
            try:
                serializers.DateField().to_internal_value(date_param)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"date": exc.detail}) from exc

    def perform_create(self, serializer: serializers.BaseSerializer) -> None:
        """Persist new habit associated with the authenticated user."""
        serializer.save(user=self.request.user)

    def _format_checkin_response(self, result: CheckInResult) -> dict[str, Any]:
        """Format a CheckInResult into a serialized dictionary."""
        return CheckInResponseSerializer(result).data

    def get_queryset(self) -> QuerySet[Habit]:
        """Return queryset filtered to the authenticated user's active or all habits."""
        user = self.request.user
        if not user or not user.is_authenticated:
            return Habit.objects.none()

        qs = Habit.objects.filter(user=user).select_related("user")
        if getattr(self, "detail", False) or self.action != "list":
            return qs

        include_archived = self.request.query_params.get("include_archived", "false").lower() in [
            "true",
            "1",
        ]
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return qs

    @extend_schema(request=None, responses={200: ArchiveResponseSerializer})
    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: str | None = None) -> Response:
        """Soft-archive a habit."""
        habit = self.get_object()
        habit.is_archived = True
        habit.save(update_fields=["is_archived", "updated_at"])
        return Response({"id": habit.id, "is_archived": True}, status=status.HTTP_200_OK)

    @extend_schema(request=None, responses={200: ArchiveResponseSerializer})
    @action(detail=True, methods=["post"])
    def unarchive(self, request: Request, pk: str | None = None) -> Response:
        """Restore an archived habit to active status."""
        habit = self.get_object()
        habit.is_archived = False
        habit.save(update_fields=["is_archived", "updated_at"])
        return Response({"id": habit.id, "is_archived": False}, status=status.HTTP_200_OK)

    @extend_schema(
        request=CheckInActionSerializer,
        responses={201: CheckInResponseSerializer, 200: CheckInResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def check(self, request: Request, pk: str | None = None) -> Response:
        """Record a habit check-in for today or a specified target date."""
        habit = self.get_object()
        serializer = CheckInActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data.get("date")

        result = check_in_habit(habit=habit, target_date=target_date, user=request.user)
        return Response(
            self._format_checkin_response(result),
            status=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        )

    @extend_schema(
        request=CheckInActionSerializer,
        responses={200: CheckInResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def uncheck(self, request: Request, pk: str | None = None) -> Response:
        """Remove a recorded check-in for today or a specified target date."""
        habit = self.get_object()
        serializer = CheckInActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data.get("date")

        result = uncheck_habit(habit=habit, target_date=target_date, user=request.user)
        return Response(
            self._format_checkin_response(result),
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="from",
                description="Filter check-ins from date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="to",
                description="Filter check-ins up to date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
        ],
        responses={200: HabitCheckInSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], url_path="check-ins")
    def check_ins(self, request: Request, pk: str | None = None) -> Response:
        """List check-ins for the habit, optionally filtered by date range and paginated."""
        habit = self.get_object()
        qs = habit.check_ins.all()

        filter_data: dict[str, Any] = {}
        if "from" in request.query_params:
            filter_data["from_date"] = request.query_params.get("from")
        if "to" in request.query_params:
            filter_data["to_date"] = request.query_params.get("to")

        filter_serializer = CheckInFilterSerializer(data=filter_data)
        if not filter_serializer.is_valid():
            return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = filter_serializer.validated_data
        if "from_date" in validated:
            qs = qs.filter(date__gte=validated["from_date"])
        if "to_date" in validated:
            qs = qs.filter(date__lte=validated["to_date"])

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = HabitCheckInSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = HabitCheckInSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
