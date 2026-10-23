from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Habit, HabitCheckIn
from .serializers import (
    HabitSerializer,
    HabitCheckInSerializer,
    CheckInActionSerializer,
    CheckInFilterSerializer,
    ArchiveResponseSerializer,
    CheckInResponseSerializer,
)
from .services.streaks import calculate_habit_streaks

class HabitViewSet(viewsets.ModelViewSet):
    queryset = Habit.objects.prefetch_related('check_ins')
    serializer_class = HabitSerializer

    def perform_create(self, serializer):
        user = self.request.user if getattr(self.request, 'user', None) and self.request.user.is_authenticated else None
        if user:
            serializer.save(user=user)
        else:
            User = get_user_model()
            default_user, _ = User.objects.get_or_create(email='default@example.com')
            serializer.save(user=default_user)

    def _format_checkin_response(self, habit, status_str: str, target_date, streaks) -> dict:
        return CheckInResponseSerializer({
            'status': status_str,
            'habit_id': habit.id,
            'date': target_date,
            'current_streak': streaks.current_streak,
            'longest_streak': streaks.longest_streak,
        }).data

    def get_queryset(self):
        qs = Habit.objects.prefetch_related('check_ins')
        if getattr(self, 'detail', False) or self.action != 'list':
            return qs

        include_archived = self.request.query_params.get('include_archived', 'false').lower() in ['true', '1']
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return qs

    @extend_schema(request=None, responses={200: ArchiveResponseSerializer})
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        habit = self.get_object()
        habit.is_archived = True
        habit.save(update_fields=['is_archived', 'updated_at'])
        return Response({'id': habit.id, 'is_archived': True}, status=status.HTTP_200_OK)

    @extend_schema(request=None, responses={200: ArchiveResponseSerializer})
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        habit = self.get_object()
        habit.is_archived = False
        habit.save(update_fields=['is_archived', 'updated_at'])
        return Response({'id': habit.id, 'is_archived': False}, status=status.HTTP_200_OK)

    @extend_schema(
        request=CheckInActionSerializer,
        responses={201: CheckInResponseSerializer, 200: CheckInResponseSerializer},
    )
    @action(detail=True, methods=['post'])
    def check(self, request, pk=None):
        habit = self.get_object()
        if habit.is_archived:
            return Response(
                {'detail': 'Cannot check in on an archived habit.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CheckInActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data.get('date') or timezone.localdate()

        checkin, created = HabitCheckIn.objects.get_or_create(habit=habit, date=target_date)
        if hasattr(habit, '_prefetched_objects_cache'):
            habit._prefetched_objects_cache.pop('check_ins', None)
        streaks = calculate_habit_streaks(habit)

        return Response(
            self._format_checkin_response(habit, 'checked', target_date, streaks),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        request=CheckInActionSerializer,
        responses={200: CheckInResponseSerializer},
    )
    @action(detail=True, methods=['post'])
    def uncheck(self, request, pk=None):
        habit = self.get_object()
        serializer = CheckInActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data.get('date') or timezone.localdate()

        checkin = HabitCheckIn.objects.filter(habit=habit, date=target_date).first()
        if not checkin:
            return Response(
                {'detail': f'No check-in found for habit {habit.id} on {target_date}.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        checkin.delete()
        if hasattr(habit, '_prefetched_objects_cache'):
            habit._prefetched_objects_cache.pop('check_ins', None)
        streaks = calculate_habit_streaks(habit)

        return Response(
            self._format_checkin_response(habit, 'unchecked', target_date, streaks),
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', description='Filter check-ins from date (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='to', description='Filter check-ins up to date (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={200: HabitCheckInSerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='check-ins')
    def check_ins(self, request, pk=None):
        habit = self.get_object()
        qs = habit.check_ins.all()

        filter_data = {}
        if 'from' in request.query_params:
            filter_data['from_date'] = request.query_params.get('from')
        if 'to' in request.query_params:
            filter_data['to_date'] = request.query_params.get('to')

        filter_serializer = CheckInFilterSerializer(data=filter_data)
        if not filter_serializer.is_valid():
            return Response(filter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = filter_serializer.validated_data
        if 'from_date' in validated:
            qs = qs.filter(date__gte=validated['from_date'])
        if 'to_date' in validated:
            qs = qs.filter(date__lte=validated['to_date'])

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = HabitCheckInSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = HabitCheckInSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
