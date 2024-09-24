from django.urls import path
from . import views


urlpatterns = [
    #회원가입, 로그인, 로그아웃, 회원탈퇴
    path('user-signup/', views.user_signup, name='user-signup'),
    path('user-login/', views.user_login, name='user-login'),
    path('user-logout/', views.user_logout, name='user-logout'),
    path('user-delete/', views.user_delete, name='user-delete'),
    
    # 캘린더 생성
    path('get-calendar/', views.get_calendar, name='get-calendar'),
    
    # SRI 검사 결과 저장 및 불러오기
    path('sri/', views.sri_list_create, name='sri-list-create'),  
    
    # 사용자의 text에 대하여 감정 분석, 대분류 감정 저장
    path('emotion-analyze-large/', views.emotion_analyze_large, name='emotion-analyze-large'),
    # 소분류 감정 입력 저장
    path('emotion-save-small/', views.emotion_save_small, name='emotion-save-small'),
    # 감정 기록 결과 저장 및 불러오기, 오늘 감정 분석 여부 판단
    path('emotion-list-create/', views.emotion_list_create, name='emotion-list-create'),
    
    # 산책 과정(시작 및 종료, 간편보고서, 만족도 저장)
    path('walk-start/', views.walk_start, name='walk-start'),
    path('walk-end/<int:walk_id>/', views.walk_end, name='walk-end'),
    path('walk-simple-report/<int:pk>/', views.walk_simple_report, name='walk-simple-report'),
    path('walk-satisfy-update/<int:pk>/', views.walk_satisfy_update, name='walk-satisfy-update'),
    
    # 산책 보고서(1개 조회, 월별 조회 )
    path('walk-once-report/<int:pk>/', views.walk_once_report, name='walk-once-report'),
    path('walk-monthly-report/<int:year>/<int:month>/', views.walk_monthly_report, name='walk-monthly-report'),
    


]
