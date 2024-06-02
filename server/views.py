from django.shortcuts import render
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from .serializers import WalkHistorySerializer, WalkHistoryEndSerializer, WalkReportSerializer, CalendarSerializer, UserSerializer
from .models import WalkHistory, Calendar, User
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


# 회원가입
@api_view(['POST'])
def user_create(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 로그인
@api_view(['POST'])
def user_login(request):
    if request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            csrf_token = get_token(request)
            return Response({"token": token.key, "csrf_token": csrf_token, "message": "Logged in successfully"}, status=status.HTTP_200_OK)
        return Response({"message": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

# 로그아웃
@api_view(['POST'])
def user_logout(request):
    if request.method == 'POST':
        request.user.auth_token.delete()
        logout(request)
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

# 회원 탈퇴
@api_view(['DELETE'])
def user_delete(request):
    if request.method == 'DELETE':
        user = request.user
        if user.is_authenticated:
            # 로그아웃 후 계정 삭제
            logout(request)
            user.delete()
            return Response({"message": "Account deleted successfully"}, status=status.HTTP_200_OK)
        return Response({"message": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
