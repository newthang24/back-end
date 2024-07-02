from datetime import datetime

from django.db.models import Avg, Sum
from django.shortcuts import render
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from .serializers import WalkHistorySerializer, WalkHistoryEndSerializer, WalkReportSerializer, CalendarSerializer, UserSerializer, SRISerializer, EmotionSerializer
from .models import WalkHistory, Calendar, User, SRI
from django.utils import timezone

#월별 산책 기록 평균 가져오기
@api_view(['GET'])
def get_monthly_stats(request, year, month):
    # 연도와 월에 해당하는 WalkHistory 객체들을 필터링
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month + 1, 1) if month != 12 else datetime(year + 1, 1, 1)
    walks = WalkHistory.objects.filter(start_time__range=(start_date, end_date))

    # 스트레스 지수 평균
    stress_avg = walks.aggregate(Avg('stable_score'))['stable_score__avg'] or 0

    # 누적 산책 거리와 시간
    total_distance = walks.aggregate(Sum('distance'))['distance__sum'] or 0
    total_time = walks.aggregate(Sum('end_time') - Sum('start_time'))['end_time__sum'] - walks.aggregate(Sum('start_time'))['start_time__sum']

    # 산책 안정도 평균
    stable_score_avg = walks.aggregate(Avg('stable_score'))['stable_score__avg'] or 0

    data = {
        'stress_avg': stress_avg,
        'total_distance': total_distance,
        'total_time': total_time,
        'stable_score_avg': stable_score_avg,
    }
    return Response(data)


#월별 캘린더 데이터 가져오기
@api_view(['GET'])
def get_monthly_calendar(request, year, month):
    # 연도와 월에 해당하는 Calendar 객체들을 필터링
    calendars = Calendar.objects.filter(year=year, month=month)

    # 각 Calendar 객체의 감정을 포함한 데이터 준비
    calendar_data = []
    for calendar in calendars:
        walk_histories = WalkHistory.objects.filter(calendar=calendar)
        walk_data = {
            'date': calendar.day,
            'emotion_large': calendar.emotion_large,
            'emotion_small': calendar.emotion_small,
            'walk_histories': list(walk_histories.values())  # WalkHistory 객체들의 리스트를 포함
        }
        calendar_data.append(walk_data)

    return Response(calendar_data)

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
    #
    # calendars = Calendar.objects.filter(year=today.year, month=today.month, day=today.day)
    # if not calendars.exists():
    #     return Response({"detail": "Calendar not found for today's date."}, status=status.HTTP_404_NOT_FOUND)
    #
    # calendar = calendars.first()
    # serializer = CalendarSerializer(calendar)
    # #return Response({"calendar_id": calendar.id}, status=status.HTTP_200_OK)
    # #return Response(serializer.data, status=status.HTTP_200_OK)
    # date_based_id = f"{today.year % 100:02d}{today.month:02d}{today.day:02d}"
    # response_data = {
    #     "calendar_id": date_based_id,
    #     **serializer.data
    # }
    # return Response(response_data, status=status.HTTP_200_OK)
    # 주어진 날짜에 해당하는 Calendar 객체를 찾거나 새로 생성합니다.
    calendar, created = Calendar.objects.get_or_create(
        year=today.year,
        month=today.month,
        day=today.day,
        user_id=request.user.id,
    )

    serializer = CalendarSerializer(calendar)
    date_based_id = f"{today.year % 100:02d}{today.month:02d}{today.day:02d}"
    response_data = {
        "calendar_id": date_based_id,
        **serializer.data
    }
    return Response(response_data, status=status.HTTP_200_OK)

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

    data['calendar'] = calendar.id
    data['start_time'] = timezone.now()
    serializer = WalkHistorySerializer(data=data)
    if serializer.is_valid():
        # serializer.save()
        # return Response(serializer.data, status=status.HTTP_201_CREATED)
        walk_history = serializer.save()  # 저장된 객체를 가져옴
        response_data = serializer.data
        response_data['id'] = walk_history.id  # 응답에 id 추가
        #return Response(response_data, status=status.HTTP_201_CREATED)
        return Response({"message": "Start walk successfully"}, status=status.HTTP_200_OK)
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
        try:
            user = User.objects.get(pk=request.user.id)
            user.add_points(10)
            #return Response(serializer.data)
            return Response({"message": "End walk successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def walk_report(request, pk):
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # serializer = WalkReportSerializer(walk)
    # return Response(serializer.data)
    user = User.objects.get(pk=request.user.id)
    #calendar = walk.calendar


    summary_data = {
        'total_time': (walk.end_time - walk.start_time) if walk.end_time and walk.start_time else None,
        'distance': walk.distance,
        'stable_score': walk.stable_score,
        'points': user.points if user else None,
        'level': user.level if user else None,
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

# SRI 점수 POST, GET
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sri_list_create(request):
    if request.method == 'GET':
        sri_scores = SRI.objects.filter(user=request.user)
        serializer = SRISerializer(sri_scores, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = SRISerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, sri_date=timezone.now())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 감정 기록 POST, GET
# @api_view(['GET', 'POST'])
# @permission_classes([IsAuthenticated])
# def emotion_list_create(request):
#     if request.method == 'GET':
#         user = request.user
#         emotions = Calendar.objects.filter(user=user)
#         serializer = EmotionSerializer(emotions, many=True)
#         return Response(serializer.data)

#     elif request.method == 'POST':
#         serializer = EmotionSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save(user=request.user)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_emotion(request):
    sentence = request.data.get('sentence')
    question = request.data.get('question')
    if not sentence:
        return Response({"detail": "Sentence is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not question:
        return Response({"detail": "Question is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Colab 모델을 사용하여 감정 분석 수행 (예시)
    # emotion_large = call_colab_model(sentence)
    emotion_large = "Happy"  # 여기에 Colab 모델을 호출하는 로직 추가

    # 오늘 날짜의 Calendar ID 조회
    user = request.user
    today = timezone.now().date()
    try:
        calendar = Calendar.objects.get(user=user, year=today.year, month=today.month, day=today.day)
    except Calendar.DoesNotExist:
        return Response({"detail": "Calendar entry does not exist for today."}, status=status.HTTP_404_NOT_FOUND)

    # 감정 결과와 질문 저장
    calendar.question = question
    calendar.emotion_large = emotion_large
    calendar.sentence = sentence
    calendar.save()

    return Response({"calendar_id": calendar.id, "emotion_large": emotion_large}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_emotion(request):
    user = request.user
    today = timezone.now().date()
    try:
        calendar = Calendar.objects.get(user=user, year=today.year, month=today.month, day=today.day)
    except Calendar.DoesNotExist:
        return Response({"detail": "Calendar entry does not exist for today."}, status=status.HTTP_404_NOT_FOUND)

    emotion_small = request.data.get('emotion_small')
    if not emotion_small:
        return Response({"detail": "Emotion small is required."}, status=status.HTTP_400_BAD_REQUEST)

    calendar.emotion_small = emotion_small
    calendar.save()

    return Response({"id": calendar.id, "question": calendar.question, "sentence": calendar.sentence, "emotion_large": calendar.emotion_large, "emotion_small": calendar.emotion_small}, status=status.HTTP_201_CREATED)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emotion_list_create(request):
    user = request.user

    if request.method == 'GET':
        emotions = Calendar.objects.filter(user=user)
        serializer = EmotionSerializer(emotions, many=True)
        return Response(serializer.data)

