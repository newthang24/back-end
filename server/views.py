import math
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
from threading import Timer

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
    total_distance = walks.aggregate(Sum('distance'))['distance__sum'] or 0 / 1000  # meters to kilometers
    total_time = sum(
        [(walk.end_time - walk.start_time).total_seconds() for walk in walks if walk.end_time and walk.start_time]) or 0
    total_time_hours = total_time / 3600  # seconds to hours

    data = {
        'message': 'successfully',
        'stress_avg': stress_avg,
        'total_distance': total_distance,  # 단위: kilometers
        'total_time': total_time_hours,  # 단위: hours
    }

    return Response(data,  status=status.HTTP_200_OK)
    #return Response({'message': 'successfully'}, status=status.HTTP_200_OK)

# 월별 캘린더 데이터 가져오기
@api_view(['GET'])
def get_monthly_calendar(request, year, month):
    # 연도와 월에 해당하는 Calendar 객체들 필터링
    calendars = Calendar.objects.filter(year=year, month=month)

    # 각 Calendar 객체의 감정을 포함한 데이터 준비
    calendar_data = []
    for calendar in calendars:
        walk_histories = WalkHistory.objects.filter(calendar=calendar)
        if walk_histories.exists() and calendar.walkfinished:  # 산책 기록이 있고 산책이 완료되었는지 확인
            walk_histories_data = []
            for walk in walk_histories:
                walk_histories_data.append({
                    'start_time': walk.start_time.strftime('%H:%M') if walk.start_time else None, #시작 시간 간략히
                    'end_time': walk.end_time.strftime('%H:%M') if walk.end_time else None, #종료 시간 간략히
                    'distance': walk.distance,
                    'stable_score': walk.stable_score,
                    'course': walk.course,
                })

            walk_data = {
                'message': 'successfully',
                'date': calendar.day,
                'emotion_large': calendar.emotion_large,
                'emotion_small': calendar.emotion_small,
                'walk_histories': walk_histories_data  # 변환된 WalkHistory 데이터 리스트를 포함
            }
            calendar_data.append(walk_data)

    return Response(calendar_data, status=status.HTTP_200_OK)
    #return Response({'message': 'successfully'}, status=status.HTTP_200_OK)

#캘린더 가져오기
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
    #주어진 날짜 기반으로 고유한 ID 생성
    date_based_id = f"{today.year % 100:02d}{today.month:02d}{today.day:02d}"
    response_data = {
        'message': 'successfully',
        "calendar_id": date_based_id,
        **serializer.data
    }
    #return Response(response_data, status=status.HTTP_200_OK)
    return Response({'message': 'successfully'}, status=status.HTTP_200_OK)


#산책 시작
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_walk(request):
    # 현재 요청을 보낸 사용자 정보 가져오기
    user = request.user
    # 오늘 날짜 기준으로 Calendar객체 가져오거나 생성
    today = timezone.now().date()
    calendar, created = Calendar.objects.get_or_create(
        year=today.year, month=today.month, day=today.day, user=user
    )
    data = request.data.copy()

    # Playtime 값을 받아옴
    playtime = data.get('playtime')
    # playtime 값이 가능한지 확인 (10, 15, 20, 25, 30분 중 하나여야 함)
    if playtime not in [10, 15, 20, 25, 30]:
        return Response({"detail": "Playtime must be one of the following values: 10, 15, 20, 25, 30 minutes."},
                        status=status.HTTP_400_BAD_REQUEST)
    #데이터에 calendar, start_time, playtime 추가
    data['calendar'] = calendar.id
    data['start_time'] = timezone.now()
    data['playtime'] = playtime  # 선택된 playtime을 저장

    #새 산책기록 생성
    serializer = WalkHistorySerializer(data=data)
    if serializer.is_valid():
        walk_history = serializer.save()
        #응답 데이터에 새로 생성된 산책 기록ID 포함
        response_data = serializer.data
        response_data['id'] = walk_history.id
        return Response({"message": "successfully", "walk_history_id": walk_history.id}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#산책 종료
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_walk(request, walk_id):
    try:
        walk_history = WalkHistory.objects.get(id=walk_id)
    #walkhistory 존재하지 않으면 404 반환
    except WalkHistory.DoesNotExist:
        return Response({"detail": f"WalkHistory with id {walk_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['end_time'] = timezone.now()

    # WalkHistory 객체 업데이트 - 시리얼라이저 설정
    serializer = WalkHistorySerializer(walk_history, data=data, partial=True)
    if serializer.is_valid():
        walk_history = serializer.save() #유효성 검사 후 업데이트된 객체 저장
        calendar = walk_history.calendar
        calendar.walkfinished = True #산책 완료
        calendar.save()

        #사용자에게 점수 추가, 레벨 관리 로직
        user = request.user
        additional_points = 2  #산책 종료시 기본 점수

        # stable_score에 따라 추가 점수 계산 (안정도가 80이상일시 3점추가, 90이상일시 5점 추가)
        stable_score = walk_history.stable_score
        if stable_score is not None:
            if stable_score >= 90:
                additional_points += 5
            elif stable_score >= 80:
                additional_points += 3

        # distance에 따라 추가 점수 계산
        distance = walk_history.distance
        if distance is not None:
            if distance >= 1500:
                additional_points += 13 #1500미터 이상일 시 13점 추가 (기본점수 포함하면 15점)
            elif distance >= 1000:
                additional_points += 8 #1000미터 이상일 시 8점 추가
            elif distance >= 500:
                additional_points += 3 #500미터 이상일 시 3점 추가
        # 추가 점수 추가, 레벨업 확인
        user.add_points(additional_points)
        #return Response({"message": "successfully", "walk_history_id": walk_history.id}, status=status.HTTP_200_OK)
        return Response({'message': 'successfully'}, status=status.HTTP_200_OK)
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
    #요청 보낸 사용자 정보 가져오기
    user = User.objects.get(pk=request.user.id)

    summary_data = {
        'message': 'successfully',
        # 총 산책 시간 분 단위로 계산
        'total_time': int(
            (walk.end_time - walk.start_time).total_seconds() / 60) if walk.end_time and walk.start_time else None,
        'distance': int(walk.distance),  #산책 거리 단위:meter
        'stable_score': int(walk.stable_score),
        #'points': user.points if user else None,
        #'level': user.level if user else None,
    }
    return Response(summary_data,  status=status.HTTP_200_OK)
    #return Response({'message': 'successfully'}, status=status.HTTP_200_OK)

#산책 기록 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def walk_history(request, pk):
    user = request.user
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    # WalkHistory 객체 직렬화
    serializer = WalkReportSerializer(walk)
    # 실제 산책 시간 계산 (tart_time과 end_time의 차이 계산)
    actual_walk_time_delta = walk.end_time - walk.start_time  #timedelta 객체
    actual_walk_time_seconds = actual_walk_time_delta.total_seconds()  #총 초로 변환
    actual_walk_time = round(actual_walk_time_seconds / 60, 2)  #분 단위로 변환하고 소수점 2자리까지 제한
    # 시작 시간과 종료 시간을 HH:MM 형식으로 변환
    start_time = walk.start_time.strftime('%H:%M')
    end_time = walk.end_time.strftime('%H:%M')
    # Calendar 모델에 있는 emotion_large 필드를 가져옴
    #main_emotion = walk.calendar.emotion_large  # 해당 산책 기록의 대분류 감정

    # response_data에 id를 walk_history_id로 변경하고 감정 분석 결과 추가
    response_data = {
        'message': 'successfully',
        'data': {
            **serializer.data,  # serializer data를 그대로 사용하되
            'walk_history_id': serializer.data['id'],  # id를 walk_history_id로 추가
            #'emotion_large': main_emotion  # Calendar의 emotion_large 필드를 추가
            'actual_walk_time': int(actual_walk_time), # 초를 분으로 변환하여 추가
            'start_time': start_time,  # HH:MM 형식으로 변환된 start_time
            'end_time': end_time,  # HH:MM 형식으로 변환된 end_time
        }
    }

    #기존 id 제거
    del response_data['data']['id']
    return Response(response_data, status=status.HTTP_200_OK)

#산책 만족도 저장
@api_view(['PATCH'])
def update_walk_score(request, pk):
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    #walk_score 값 가져오기
    walk_score = request.data.get('walk_score')
    if walk_score is not None:
        # walk_score 존재할 경우 업데이트
        walk.walk_score = walk_score
        walk.save()
        #return Response({"detail": "successfully."}, status=status.HTTP_200_OK)
        return Response({'message': 'successfully'}, status=status.HTTP_200_OK)
    return Response({"detail": "Walk score is required."}, status=status.HTTP_400_BAD_REQUEST)


# 회원가입
@api_view(['POST'])
def user_create(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            #토큰 response에 띄워야할 경우
            return Response({'token': token.key, "message": "successfully"}, status=status.HTTP_201_CREATED)
            #message 만 띄워도 될 경우
            #return Response({'message': 'successfully'}, status=status.HTTP_201_CREATED)
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
            #token, csrf_token 모두 response에 띄움
            return Response({"token": token.key, "csrf_token": csrf_token, "message": "successfully"}, status=status.HTTP_200_OK)
            #return Response({'message': 'successfully'}, status=status.HTTP_200_OK)
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
        #지금까지의 산책 횟수 계산
        walk_count = WalkHistory.objects.filter(calendar__user=request.user).count()

        #SRI 검사를 해야 할지 여부 판단
        sri_needed = (walk_count == 0) or (walk_count % 5 == 0)

        #오늘 SRI 검사를 했는지 여부 확인
        today = timezone.now().date()
        #today_sri = SRI.objects.filter(user=request.user, sri_date__date=today).exists()
        today_sri_done = SRI.objects.filter(user=request.user, sri_date__date=today).exists()

        if today_sri_done:
            sri_needed = False
        response_data = {
            'message': 'successfully',
            #'sri_scores': serializer.data,
            #'walk_count': walk_count, #필요없대
            'sri_needed': sri_needed,
            #'today_sri_done': today_sri_done  # 오늘 SRI 검사를 했는지 여부
        }

        return Response(response_data, status=status.HTTP_200_OK)
        #return Response({'message': 'successfully'}, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        serializer = SRISerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, sri_date=timezone.now())
            #return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response({'message': 'successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 사용자의 text를 바탕으로 감정 분석 및 대분류 감정 저장
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
    colab_url = "https://newthangcolab.ngrok.app/predict"  # Colab 실행하면 Colab과 자동으로 연결되도록 하는 endpoint
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

    #return Response({"calendar_id": calendar.id, "emotion_large": emotion_large}, status=status.HTTP_200_OK)
    # 성공 메시지뿐만 아니라 감정분석이 잘되어 대분류 감정을 저장했는지 확인
    return Response({'message': 'successfully', "emotion_large": emotion_large}, status=status.HTTP_200_OK)


# 소분류 감정 저장(사용자가 대분류 감정을 토대로 세부 감정 직접 선택)
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


    # return Response({"id": calendar.id, "question": calendar.question, "sentence": calendar.sentence,
    #                 "emotion_large": calendar.emotion_large, "emotion_small": calendar.emotion_small},
    #                 status=status.HTTP_201_CREATED)
    return Response({'message': 'successfully'}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emotion_list_create(request):
    user = request.user

    # 오늘 날짜를 구함
    today = timezone.now().date()

    # 오늘 날짜에 해당하는 감정 분석이 있는지 확인
    today_emotion_exists = Calendar.objects.filter(user=user, year=today.year, month=today.month,
                                                day=today.day).exists()
    if request.method == 'GET':
        emotions = Calendar.objects.filter(user=user)
        serializer = EmotionSerializer(emotions, many=True)
        #return Response(serializer.data)
        #return Response({'message': 'successfully'}, status=status.HTTP_200_OK)
        emotions_data = serializer.data
        for emotion in emotions_data:
            emotion['calendar_id'] = emotion.pop('id')  #'id'를 'calendar_id'로 변경(Calender Model의 고유한 pk id를 가리킴)

        response_data = {
            'message': 'successfully',
            'emotions': serializer.data,
            'today_emotion_done': today_emotion_exists  #오늘 감정 분석 여부
        }

        return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_record(request, year, month):
    user = request.user
    year = int(year)  # URL 경로 파라미터로 받은 연도를 정수로 변환
    month = int(month)  # URL 경로 파라미터로 받은 월을 정수로 변환

    # 선인장 레벨 및 점수
    cactus_level = user.level
    score = user.points

    # 회원의 닉네임
    nickname = user.nickname

    # 가장 최근의 SRI 검사 결과
    latest_sri = SRI.objects.filter(user=user).order_by('-sri_date').first()
    sri_score = latest_sri.sri_score if latest_sri else None
    sri_date = latest_sri.sri_date.strftime('%Y.%m.%d') if latest_sri else None

    # 최근 7개의 SRI 검사 결과
    recent_sri_scores = SRI.objects.filter(user=user).order_by('-sri_date')[:7].values('sri_date', 'sri_score')
    sri_scores = [{'date': score['sri_date'].strftime('%Y-%m-%d'), 'sri_score': score['sri_score']} for score in
                recent_sri_scores]
    sri_score_values = [score['sri_score'] for score in sri_scores if score['sri_score'] is not None]
    sri_average = mean(sri_score_values) if sri_score_values else None

    # 해당 월 동안의 누적 산책 거리 및 시간
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    walks = WalkHistory.objects.filter(calendar__user=user, start_time__range=(start_date, end_date))

    total_distance = (walks.aggregate(Sum('distance'))['distance__sum'] or 0) / 1000  # meters to kilometers

    total_time_seconds = sum(
        [(walk.end_time - walk.start_time).total_seconds() for walk in walks if walk.end_time and walk.start_time]) or 0
    total_time_minutes = total_time_seconds // 60
    total_time_hours = total_time_seconds / 3600  # seconds to hours

    # 해당 월 동안의 산책을 한 날의 감정 분석 결과 대분류 값 및 날짜
    emotions = Calendar.objects.filter(user=user, year=year, month=month, walkfinished=True)

    # 감정 분석 결과를 날짜와 함께 리스트로 구성
    emotion_analysis = []
    for emotion in emotions:
        # 해당 날짜의 첫 번째 산책 기록 가져오기
        #first_walk = WalkHistory.objects.filter(calendar=emotion).order_by('start_time').first()
        #walkhistory_id = first_walk.id if first_walk else None

        # 수정된 코드: 해당 날짜의 모든 산책 기록의 ID 가져오기
        walks_on_day = WalkHistory.objects.filter(calendar=emotion).order_by('start_time')  # 수정된 부분
        walkhistory_id = [walk.id for walk in walks_on_day]  # 수정된 부분

        emotion_data = {
            'date': emotion.day,
            'emotion': emotion.emotion_large,
            'walkhistory_id': walkhistory_id
        }
        emotion_analysis.append(emotion_data)

    # 가장 최근 7개의 stable_score를 가져옴
    recent_stable_scores = WalkHistory.objects.filter(calendar__user=user).order_by('-start_time')[:7].values(
        'start_time', 'stable_score')
    stable_scores = [{'date': score['start_time'].date(), 'stable_score': score['stable_score']} for score in
                    recent_stable_scores]
    stable_score_values = [score['stable_score'] for score in stable_scores if score['stable_score'] is not None]
    stable_average = mean(stable_score_values) if stable_score_values else None

    data = {
        'message': 'successfully',
        "nickname": nickname,
        "cactus_level": cactus_level,
        "cactus_score": score,
        "sri_score": sri_score,
        "sri_date": sri_date,
        "total_distance": math.floor(total_distance * 10) / 10,  # kilometers
        "total_time": math.floor(total_time_hours * 10) / 10,  # hours
        "emotion_analysis": emotion_analysis,
        "stable_scores": stable_scores,
        "stable_average": stable_average,
        "sri_scores": sri_scores,
        "sri_average": sri_average
    }

    return Response(data, status=status.HTTP_200_OK)
