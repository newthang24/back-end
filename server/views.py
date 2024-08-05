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
from statistics import mean
from django.db.models import Count
import requests

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
        'message':'successfully',
        'stress_avg': stress_avg,
        'total_distance': total_distance,
        'total_time': total_time,
        'stable_score_avg': stable_score_avg,
    }
    return Response(data,  status=status.HTTP_200_OK)

# 월별 캘린더 데이터 가져오기
@api_view(['GET'])
def get_monthly_calendar(request, year, month):
    # 연도와 월에 해당하는 Calendar 객체들을 필터링
    calendars = Calendar.objects.filter(year=year, month=month)

    # 각 Calendar 객체의 감정을 포함한 데이터 준비
    calendar_data = []
    for calendar in calendars:
        walk_histories = WalkHistory.objects.filter(calendar=calendar)
        if walk_histories.exists() and calendar.walkfinished:  # 산책 기록이 있고 산책이 완료되었는지 확인
            username = calendar.user.username if calendar.user else 'Unknown'
            walk_data = {
                'message': 'successfully',
                'date': calendar.day,
                'emotion_large': calendar.emotion_large,
                'emotion_small': calendar.emotion_small,
                'walk_histories': list(walk_histories.values())  # WalkHistory 객체들의 리스트를 포함
            }
            calendar_data.append(walk_data)

    return Response(calendar_data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_calendar(request):
    today = timezone.now()
    calendar, created = Calendar.objects.get_or_create(
        year=today.year,
        month=today.month,
        day=today.day,
        user_id=request.user.id,
    )

    # 산책이 완료되었는지 확인
    if not calendar.walkfinished:
        calendar.emotion_large = None
        calendar.emotion_small = None

    serializer = CalendarSerializer(calendar)
    date_based_id = f"{today.year % 100:02d}{today.month:02d}{today.day:02d}"
    response_data = {
        'message': 'successfully',
        "calendar_id": date_based_id,
        **serializer.data
    }
    return Response(response_data, status=status.HTTP_200_OK)


#산책 시작
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_walk(request):
    user = request.user
    today = timezone.now().date()
    calendar, created = Calendar.objects.get_or_create(
        year=today.year, month=today.month, day=today.day, user=user
    )
    data = request.data.copy()

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
        walk_history = serializer.save()  # 저장된 객체를 가져옴
        response_data = serializer.data
        response_data['id'] = walk_history.id  # 응답에 id 추가
        return Response({"message": "successfully", "walk_history_id": walk_history.id}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_walk(request, walk_id):
    try:
        walk_history = WalkHistory.objects.get(id=walk_id)
    except WalkHistory.DoesNotExist:
        return Response({"detail": f"WalkHistory with id {walk_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['end_time'] = timezone.now()

    serializer = WalkHistorySerializer(walk_history, data=data, partial=True)
    if serializer.is_valid():
        walk_history = serializer.save()
        calendar = walk_history.calendar
        calendar.walkfinished = True
        calendar.save()
        return Response({"message": "successfully", "walk_history_id": walk_history.id}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#산책 종료 후 결과 (간편 보고서) 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def walk_report(request, pk):
    #user = request.user
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    user = User.objects.get(pk=request.user.id)

    summary_data = {
        'message':'successfully',
        'total_time': (walk.end_time - walk.start_time) if walk.end_time and walk.start_time else None,
        'distance': walk.distance,
        'stable_score': walk.stable_score,
        'points': user.points if user else None,
        'level': user.level if user else None,
    }
    return Response(summary_data,  status=status.HTTP_200_OK)

#산책 기록 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def walk_history(request, pk):
    user = request.user

    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


    serializer = WalkReportSerializer(walk)
    response_data = {
        'message': 'successfully',
        'data': serializer.data
    }

    return Response(response_data,   status=status.HTTP_200_OK)

#산책 만족도 저장
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
        return Response({"detail": "successfully."}, status=status.HTTP_200_OK)
    return Response({"detail": "Walk score is required."}, status=status.HTTP_400_BAD_REQUEST)


# 회원가입
@api_view(['POST'])
def user_create(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, "message": "successfully"}, status=status.HTTP_201_CREATED)
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
            return Response({"token": token.key, "csrf_token": csrf_token, "message": "successfully"}, status=status.HTTP_200_OK)
        return Response({"message": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

# 로그아웃
@api_view(['POST'])
def user_logout(request):
    if request.method == 'POST':
        request.user.auth_token.delete()
        logout(request)
        return Response({"message": "successfully"}, status=status.HTTP_200_OK)

# 회원 탈퇴
@api_view(['DELETE'])
def user_delete(request):
    if request.method == 'DELETE':
        user = request.user
        if user.is_authenticated:
            # 로그아웃 후 계정 삭제
            logout(request)
            user.delete()
            return Response({"message": "successfully"}, status=status.HTTP_200_OK)
        return Response({"message": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

# SRI 점수 POST, GET
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def sri_list_create(request):
    if request.method == 'GET':
        sri_scores = SRI.objects.filter(user=request.user)
        serializer = SRISerializer(sri_scores, many=True)
        #return Response(serializer.data)
        # 지금까지의 산책 횟수를 계산
        walk_count = WalkHistory.objects.filter(calendar__user=request.user).count()

        # SRI 검사를 해야 할지 여부를 판단
        sri_needed = (walk_count == 0) or (walk_count % 5 == 0)

        # 오늘 SRI 검사를 했는지 여부 확인
        today = timezone.now().date()
        today_sri = SRI.objects.filter(user=request.user, sri_date__date=today).exists()

        response_data = {
            'sri_scores': serializer.data,
            'walk_count': walk_count,
            'sri_needed': sri_needed,
            'today_sri_done': today_sri  # 오늘 SRI 검사를 했는지 여부
        }

        return Response(response_data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = SRISerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, sri_date=timezone.now())
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_emotion(request):
    sentence = request.data.get('sentence')
    question = request.data.get('question')
    if not sentence:
        return Response({"detail": "Sentence is required."}, status=status.HTTP_400_BAD_REQUEST)
    if not question:
        return Response({"detail": "Question is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Colab 모델을 사용하여 감정 분석 수행
    colab_url = "https://9d29-34-19-89-121.ngrok-free.app/predict"  # 여기에 ngrok Public URL을 입력
    try:
        response = requests.post(colab_url, json={'text': sentence})
        response_data = response.json()
        emotion_large = response_data.get('emotion', 'Unknown')
    except requests.exceptions.RequestException as e:
        return Response({"detail": f"Error contacting Colab server: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


    return Response({"id": calendar.id, "question": calendar.question, "sentence": calendar.sentence,
                    "emotion_large": calendar.emotion_large, "emotion_small": calendar.emotion_small},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emotion_list_create(request):
    user = request.user

    if request.method == 'GET':
        emotions = Calendar.objects.filter(user=user)
        serializer = EmotionSerializer(emotions, many=True)
        return Response(serializer.data)


# record 화면
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_record(request, month):
    user = request.user
    year = datetime.now().year  # 현재 연도를 사용
    month = int(month)  # URL 경로 파라미터로 받은 월을 정수로 변환

    # 선인장 레벨 및 점수
    cactus_level = user.level
    score = user.points

    # 가장 최근의 SRI 검사 결과
    latest_sri = SRI.objects.filter(user=user).order_by('-sri_date').first()
    sri_score = latest_sri.sri_score if latest_sri else None
    sri_date = latest_sri.sri_date.strftime('%Y.%m.%d') if latest_sri else None

    # 최근 7개의 SRI 검사 결과
    recent_sri_scores = SRI.objects.filter(user=user).order_by('-sri_date')[:7].values('sri_date', 'sri_score')
    sri_scores = [{'date': score['sri_date'].strftime('%Y-%m-%d'), 'sri_score': score['sri_score']} for score in recent_sri_scores]
    sri_score_values = [score['sri_score'] for score in sri_scores if score['sri_score'] is not None]
    sri_average = mean(sri_score_values) if sri_score_values else None

    # 해당 월 동안의 누적 산책 거리 및 시간
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    walks = WalkHistory.objects.filter(calendar__user=user, start_time__range=(start_date, end_date))

    total_distance = walks.aggregate(Sum('distance'))['distance__sum'] or 0

    # Calculate total time in seconds
    total_time_seconds = sum([(walk.end_time - walk.start_time).total_seconds() for walk in walks if walk.end_time and walk.start_time]) or 0

    # Convert total_time from seconds to minutes
    total_time_minutes = total_time_seconds // 60

    # 해당 월 동안의 산책을 한 날의 감정 분석 결과 대분류 값 및 날짜
    emotions = Calendar.objects.filter(user=user, year=year, month=month, walkfinished=True).values('day', 'emotion_large')

    # 감정 분석 결과를 날짜와 함께 리스트로 구성
    emotion_analysis = [{'date': emotion['day'], 'emotion': emotion['emotion_large']} for emotion in emotions]

    # 가장 최근 7개의 stable_score를 가져옴
    recent_stable_scores = WalkHistory.objects.filter(calendar__user=user).order_by('-start_time')[:7].values('start_time', 'stable_score')
    stable_scores = [{'date': score['start_time'].date(), 'stable_score': score['stable_score']} for score in recent_stable_scores]
    stable_score_values = [score['stable_score'] for score in stable_scores if score['stable_score'] is not None]
    stable_average = mean(stable_score_values) if stable_score_values else None

    data = {
        "cactus_level": cactus_level,
        "score": score,
        "sri_score": sri_score,
        "sri_date": sri_date,
        "total_distance": total_distance,
        "total_time": total_time_minutes,
        "emotion_analysis": emotion_analysis,
        "stable_scores": stable_scores,
        "stable_average": stable_average,
        "sri_scores": sri_scores,
        "sri_average": sri_average
    }

    return Response(data, status=status.HTTP_200_OK)