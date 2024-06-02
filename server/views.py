from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from .serializers import WalkHistorySerializer, WalkHistoryEndSerializer, WalkReportSerializer, CalendarSerializer
from .models import WalkHistory, Calendar
from django.utils import timezone


# @api_view(['POST'])
# def create_calendar(request):
#     data = request.data.copy()
#     data['year'] = timezone.now().year
#     data['month'] = timezone.now().month
#     data['day'] = timezone.now().day
#
#     serializer = CalendarSerializer(data=data)
#     if serializer.is_valid():
#         serializer.save()
#         return Response(serializer.data, status=status.HTTP_201_CREATED)
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_calendar(request):
    today = timezone.now()
    calendars = Calendar.objects.filter(year=today.year, month=today.month, day=today.day)
    if not calendars.exists():
        return Response({"detail": "Calendar not found for today's date."}, status=status.HTTP_404_NOT_FOUND)

    calendar = calendars.first()
    serializer = CalendarSerializer(calendar)
    return Response(serializer.data, status=status.HTTP_200_OK)
@api_view(['POST'])
def start_walk(request):
    data = request.data.copy()

    # 주어진 날짜에 해당하는 Calendar 객체가 있는지 확인
    # calendar, created = Calendar.objects.get_or_create(
    #     year=timezone.now().year,
    #     month=timezone.now().month,
    #     day=timezone.now().day
    # )
    calendar_id = data.get('calendar')
    if not calendar_id:
        return Response({"detail": "Calendar ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        calendar = Calendar.objects.get(id=calendar_id)
    except Calendar.DoesNotExist:
        return Response({"detail": "Calendar not found."}, status=status.HTTP_404_NOT_FOUND)

    # data['calendar'] = calendar.id
    data['start_time'] = timezone.now()
    serializer = WalkHistorySerializer(data=data)
    if serializer.is_valid():
        # serializer.save()
        # return Response(serializer.data, status=status.HTTP_201_CREATED)
        walk_history = serializer.save()  # 저장된 객체를 가져옴
        response_data = serializer.data
        response_data['id'] = walk_history.id  # 응답에 id 추가
        return Response(response_data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def end_walk(request, pk):
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['end_time'] = timezone.now()

    serializer = WalkHistoryEndSerializer(walk, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def walk_report(request, pk):
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # serializer = WalkReportSerializer(walk)
    # return Response(serializer.data)
    summary_data = {
        'total_time': (walk.end_time - walk.start_time) if walk.end_time and walk.start_time else None,
        'distance': walk.distance,
        'stable_score': walk.stable_score,
    }
    return Response(summary_data, status=status.HTTP_200_OK)

@api_view(['GET'])
def walk_history(request, pk):
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    serializer = WalkReportSerializer(walk)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PATCH'])
def update_walk_score(request, pk):
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    walk_score = request.data.get('walk_score')
    if walk_score is not None:
        walk.walk_score = walk_score
        walk.save()
        return Response({"detail": "Walk score updated successfully."}, status=status.HTTP_200_OK)
    return Response({"detail": "Walk score is required."}, status=status.HTTP_400_BAD_REQUEST)
