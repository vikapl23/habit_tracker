from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection
from django.db.models import Q, QuerySet
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Habit
from .serializers import (
    ArchiveResponseSerializer,
    CheckInActionSerializer,
    CheckInFilterSerializer,
    CheckInResponseSerializer,
    HabitCheckInSerializer,
    HabitSerializer,
    HabitStatisticsSerializer,
    UserSummaryStatisticsSerializer,
)
from .services import CheckInResult, check_in_habit, uncheck_habit
from .services.statistics import (
    calculate_habit_statistics,
    calculate_user_summary_statistics,
)


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
        if "scheduled_today" in request.query_params:
            val = request.query_params.get("scheduled_today", "").lower()
            if val not in ["true", "1", "false", "0"]:
                raise serializers.ValidationError(
                    {"scheduled_today": "Must be a valid boolean ('true', 'false', '1', or '0')."}
                )

    def perform_create(self, serializer: serializers.BaseSerializer) -> None:
        """Persist new habit associated with the authenticated user."""
        serializer.save(user=self.request.user)

    def _format_checkin_response(self, result: CheckInResult) -> dict[str, Any]:
        """Format a CheckInResult into a serialized dictionary."""
        return CheckInResponseSerializer(result).data

    def _get_target_date(self) -> date:
        """Resolve evaluation target date from query parameters or default to user's today."""
        if "date" in self.request.query_params:
            try:
                return serializers.DateField().to_internal_value(self.request.query_params["date"])
            except serializers.ValidationError:
                pass
        user = self.request.user
        if user and hasattr(user, "get_today"):
            return user.get_today()
        return timezone.localdate()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="include_archived",
                description="Include archived habits in results (default false)",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="scheduled_today",
                description="Filter habits scheduled today (true/false)",
                required=False,
                type=bool,
            ),
            OpenApiParameter(
                name="date",
                description="Evaluation date for is_checked_today and is_scheduled_today (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
        ]
    )
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """List active habits for the user with streak and schedule metadata."""
        return super().list(request, *args, **kwargs)

    def get_queryset(self) -> QuerySet[Habit]:
        """Return queryset filtered to the authenticated user's active or all habits."""
        user = self.request.user
        if not user or not user.is_authenticated:
            return Habit.objects.none()

        qs = Habit.objects.filter(user=user).select_related("user")
        if getattr(self, "detail", False) or self.action != "list":
            return qs

        if "date" in self.request.query_params:
            qs = qs.prefetch_related("check_ins")

        include_archived = self.request.query_params.get("include_archived", "false").lower() in [
            "true",
            "1",
        ]
        if not include_archived:
            qs = qs.filter(is_archived=False)

        if "scheduled_today" in self.request.query_params:
            param = self.request.query_params.get("scheduled_today", "").lower()
            if param in ["true", "1", "false", "0"]:
                target_date = self._get_target_date()
                target_weekday = target_date.weekday()
                want_scheduled = param in ["true", "1"]

                if connection.vendor == "postgresql":
                    contains_lookup = Q(frequency_days__contains=target_weekday)
                else:
                    contains_lookup = Q(frequency_days__icontains=str(target_weekday))

                if want_scheduled:
                    qs = qs.filter(Q(frequency_type="daily") | contains_lookup)
                else:
                    qs = qs.filter(frequency_type="custom").exclude(contains_lookup)

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

    @extend_schema(
        responses={200: HabitStatisticsSerializer},
        description="Get habit statistics including completion rate for last 7 and 30 days, total check-ins, and streaks.",
    )
    @action(detail=True, methods=["get"])
    def statistics(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve completion rates and streak analytics for the habit."""
        habit = self.get_object()
        stats = calculate_habit_statistics(habit, user=request.user)
        serializer = HabitStatisticsSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StatisticsSummaryView(APIView):
    """View for retrieving overall user statistics summary."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: UserSummaryStatisticsSerializer},
        description="Retrieve overall completion rate this week and this month, best habit, active habits, and total check-ins.",
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        summary = calculate_user_summary_statistics(request.user)
        serializer = UserSummaryStatisticsSerializer(summary)
        return Response(serializer.data, status=status.HTTP_200_OK)
