from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Habit, HabitCheckIn, CheckIn
from .serializers import HabitSerializer, HabitCheckInSerializer, CheckInActionSerializer

class HabitViewSet(viewsets.ModelViewSet):
    queryset = Habit.objects.all()
    serializer_class = HabitSerializer

    def get_queryset(self):
        qs = Habit.objects.all()
        # In detail routes (like archive/unarchive, check/uncheck/check-ins), allow accessing habit
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'archive', 'unarchive', 'check', 'uncheck', 'check_ins']:
            return qs

        include_archived = self.request.query_params.get('include_archived', 'false').lower() in ['true', '1']
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return qs

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        habit = self.get_object()
        habit.is_archived = True
        habit.save(update_fields=['is_archived', 'updated_at'])
        return Response({'id': habit.id, 'is_archived': True}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        habit = self.get_object()
        habit.is_archived = False
        habit.save(update_fields=['is_archived', 'updated_at'])
        return Response({'id': habit.id, 'is_archived': False}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def check(self, request, pk=None):
        habit = self.get_object()
        serializer = CheckInActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data.get('date') or timezone.localdate()

        checkin, created = HabitCheckIn.objects.get_or_create(habit=habit, date=target_date)

        return Response(
            {
                'status': 'checked',
                'habit_id': habit.id,
                'date': str(target_date),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
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

        return Response(
            {
                'status': 'unchecked',
                'habit_id': habit.id,
                'date': str(target_date),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['get'], url_path='check-ins')
    def check_ins(self, request, pk=None):
        habit = self.get_object()
        qs = habit.check_ins.all()

        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        serializer = HabitCheckInSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
