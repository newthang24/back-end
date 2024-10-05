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
from rest_framework.permissions import AllowAny

# 회원가입
@api_view(['POST'])
@permission_classes([AllowAny])
def user_signup(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key, "message": "successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 로그인
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    if request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "message": "successfully"}, status=status.HTTP_200_OK)
        return Response({"message": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)

# 로그아웃
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 인증된 사용자만 접근 가능
def user_logout(request):
    if request.method == 'POST':
        request.user.auth_token.delete()
        return Response({"message": "successfully"}, status=status.HTTP_200_OK)

# 회원 탈퇴
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request):
    if request.method == 'DELETE':
        user = request.user
        if user.is_authenticated:
            user.auth_token.delete()
            user.delete()
            return Response({"message": "successfully"}, status=status.HTTP_200_OK)
        return Response({"message": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)


#캘린더 가져오기
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_calendar(request):
    # 오늘 날짜를 자동으로 가져옴
    today = timezone.now()
    year = today.year
    month = today.month
    day = today.day

    # 사용자의 ID를 가져옴
    user_id = request.user.id

    try:
        # 오늘 날짜에 해당하는 Calendar 객체를 가져옴. 존재하지 않으면 새로 생성.
        calendar, created = Calendar.objects.get_or_create(
            year=year,
            month=month,
            day=day,
            user_id=user_id,
        )

        # 캘린더가 새로 생성된 경우만 감정 데이터를 리셋
        if created:
            calendar.emotion_large = None
            calendar.emotion_small = None
            calendar.save()

        # 고유한 calendar_id 생성
        date_based_id = f"{year % 100:02d}{month:02d}{day:02d}"

        # 직렬화된 데이터 준비
        serializer = CalendarSerializer(calendar)

        # 응답 데이터를 준비
        response_data = {
            'message': 'Calendar created successfully' if created else 'Calendar already exists',
            "calendar_id": date_based_id,
            **serializer.data
        }

        return Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except Exception as e:
        # 오류 발생 시, 500 상태 코드와 함께 오류 메시지를 반환합니다.
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
def emotion_analyze_large(request):
    sentence = request.data.get('sentence')
    #question = request.data.get('question')
    if not sentence:
        return Response({"detail": "Sentence is required."}, status=status.HTTP_400_BAD_REQUEST)
    #if not question:
    #    return Response({"detail": "Question is required."}, status=status.HTTP_400_BAD_REQUEST)

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
    #calendar.question = question
    calendar.emotion_large = emotion_large
    calendar.sentence = sentence
    calendar.save()

    #return Response({"calendar_id": calendar.id, "emotion_large": emotion_large}, status=status.HTTP_200_OK)
    # 성공 메시지뿐만 아니라 감정분석이 잘되어 대분류 감정을 저장했는지 확인
    return Response({'message': 'successfully', "emotion_large": emotion_large}, status=status.HTTP_200_OK)


# 소분류 감정 저장(사용자가 대분류 감정을 토대로 세부 감정 직접 선택)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def emotion_save_small(request):
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

    return Response({'message': 'successfully'}, status=status.HTTP_201_CREATED)

# 감정 기록 결과 저장 및 불러오기, 오늘 감정 분석 여부 판단
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emotion_list_create(request):
    user = request.user

    # 클라이언트에서 쿼리 파라미터로 받은 날짜값(todayDate)을 가져옴
    today_date_str = request.query_params.get('todayDate')

    if not today_date_str:
        return Response({"detail": "todayDate parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    # 날짜 문자열을 파싱하여 년도, 월, 일로 변환
    try:
        date_obj = datetime.strptime(today_date_str, '%Y-%m-%d').date()
        year = date_obj.year
        month = date_obj.month
        day = date_obj.day
    except ValueError:
        return Response({"detail": "Invalid todayDate format. Expected 'YYYY-MM-DD'."}, status=status.HTTP_400_BAD_REQUEST)

    # 해당 날짜에 해당하는 감정 분석 기록을 가져옴
    try:
        calendar_record = Calendar.objects.filter(user=user, year=year, month=month, day=day).first()
        if not calendar_record or not calendar_record.emotion_large:
            return Response({
                'message': 'No emotion data found for the specified date.',
                'today_emotion_done': False
            }, status=status.HTTP_200_OK)
    except Calendar.DoesNotExist:
        return Response({
            'message': 'No emotion data found for the specified date.',
            'today_emotion_done': False
        }, status=status.HTTP_200_OK)
    except Exception as e:
        # 추가적인 예외를 잡아내기 위한 블록
        return Response({"detail": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 감정 데이터가 존재할 경우, 직렬화
    serializer = EmotionSerializer(calendar_record)
    emotions_data = serializer.data

    print(f"Serialized emotions data: {emotions_data}")

    # 감정 데이터가 딕셔너리인지 확인
    if isinstance(emotions_data, dict):
        # 감정 데이터에 날짜 정보 추가
        emotions_data['calendar_id'] = emotions_data.get('id')  # 'id'를 'calendar_id'로 복사
        emotions_data['date'] = f"{year}-{month:02d}-{day:02d}"  # 날짜를 'YYYY-MM-DD' 형식으로 추가
        del emotions_data['id']  # 'id' 키를 제거
    else:
        return Response({"detail": "Invalid data format from serializer."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    response_data = {
        'message': 'successfully',
        'today_emotion_done': True,  # 해당 날짜에 감정 분석 여부
        'emotions': emotions_data  # 해당 날짜의 감정 기록 리스트
    }

    return Response(response_data, status=status.HTTP_200_OK)

#산책 시작
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def walk_start(request):
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
    # playtime 값이 가능한지 확인 (5,10, 15, 20, 25, 30분 중 하나여야 함)
    if playtime not in [5, 10, 15, 20, 25, 30]:
        return Response({"detail": "Playtime must be one of the following values: 5, 10, 15, 20, 25, 30 minutes."},
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
def walk_end(request, walk_id):
    try:
        walk_history = WalkHistory.objects.get(id=walk_id)
    #walkhistory 존재하지 않으면 404 반환
    except WalkHistory.DoesNotExist:
        return Response({"detail": f"WalkHistory with id {walk_id} does not exist."}, status=status.HTTP_404_NOT_FOUND)

    data = request.data.copy()
    data['end_time'] = timezone.now()

    # 키넥트 데이터 처리
    kinect_data = request.data.get('kinect_data')
    if not kinect_data:
        return Response({"detail": "No Kinect data provided."}, status=status.HTTP_400_BAD_REQUEST)

    # WalkHistory의 stable_score 업데이트
    walk_history.stable_score = kinect_data

    # WalkHistory 객체 업데이트 - 시리얼라이저 설정
    serializer = WalkHistorySerializer(walk_history, data=data, partial=True)
    if serializer.is_valid():
        walk_history = serializer.save() #유효성 검사 후 업데이트된 객체 저장
        calendar = walk_history.calendar
        calendar.walkfinished = True #산책 완료
        calendar.save()

        #사용자에게 점수 추가, 레벨 관리 로직
        user = request.user
        additional_points = 7  #산책 종료시 기본 점수

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

#산책 종료 후 즉시 뜨는 간편 보고서 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def walk_simple_report(request, pk):
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

#산책 만족도 저장
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def walk_satisfy_update(request, pk):
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # walk_score 값 가져오기
    walk_score = request.data.get('walk_score')
    if walk_score is not None:
        # walk_score 존재할 경우 업데이트
        walk.walk_score = walk_score
        walk.save()
        return Response({'message': 'successfully'}, status=status.HTTP_200_OK)
    
    return Response({"detail": "Walk score is required."}, status=status.HTTP_400_BAD_REQUEST)

# 1개의 산책 기록 조회
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def walk_once_report(request, pk):
    user = request.user
    try:
        walk = WalkHistory.objects.get(pk=pk)
    except WalkHistory.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    # WalkHistory 객체 직렬화
    serializer = WalkReportSerializer(walk)
    # 실제 산책 시간 계산 (start_time과 end_time이 존재할 때만 계산)
    if walk.start_time and walk.end_time:
        actual_walk_time_delta = walk.end_time - walk.start_time
        actual_walk_time_seconds = actual_walk_time_delta.total_seconds()
        actual_walk_time = round(actual_walk_time_seconds / 60, 2)  # 분 단위로 변환
    else:
        actual_walk_time = 0  # 시작 시간 또는 종료 시간이 없으면 0분으로 설정

    # 시작 시간과 종료 시간을 HH:MM 형식으로 변환 (start_time 또는 end_time이 None일 경우 처리)
    start_time = walk.start_time.strftime('%H:%M') if walk.start_time else '00:00'
    end_time = walk.end_time.strftime('%H:%M') if walk.end_time else '00:00'

    # Calendar 모델에 있는 emotion_large 필드를 가져옴
    #emotion_large = walk.calendar.emotion_large  # 해당 산책 기록의 대분류 감정
    #emotion_small = walk.calendar.emotion_small
    # response_data에 id를 walk_history_id로 변경하고 감정 분석 결과 추가
    response_data = {
        'message': 'successfully',
        'start_time': start_time,
        'end_time': end_time,
        'distance': walk.distance,
        'actual_walk_time': int(actual_walk_time),
        'walk_score': walk.walk_score,
        'stable_score': walk.stable_score,
        'walk_history_id': serializer.data['id'],
        #'emotion_large': emotion_large,
        #'emotion_small': emotion_small,
    }

    #기존 id 제거
    #del response_data['data']['id']
    return Response(response_data, status=status.HTTP_200_OK)


# 월별 산책 기록 조회(record 화면 구성)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def walk_monthly_report(request, year, month):
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
    sri_date = latest_sri.sri_date.strftime('%Y-%m-%d') if latest_sri else None

    # 최근 7개의 SRI 검사 결과
    recent_sri_scores = SRI.objects.filter(user=user).order_by('-sri_date')[:7].values('sri_date', 'sri_score')
    sri_scores = [{'date': score['sri_date'].strftime('%m/%d'), 'sri_score': score['sri_score']} for score in
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
            'date': f"{emotion.year:04d}-{emotion.month:02d}-{emotion.day:02d}",
            'emotion': emotion.emotion_large,
            'walkhistory_id': walkhistory_id
        }
        emotion_analysis.append(emotion_data)

    # 가장 최근 7개의 stable_score를 가져옴
    recent_stable_scores = WalkHistory.objects.filter(calendar__user=user).order_by('-start_time')[:7].values(
        'start_time', 'stable_score')
    stable_scores = [{'date': score['start_time'].strftime('%m/%d'), 'stable_score': score['stable_score']} for score in
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
