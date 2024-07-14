from django.urls import path
from . import views

urlpatterns = [

    path('start-walk/', views.start_walk, name='start-walk'),
    path('end-walk/<int:pk>/', views.end_walk, name='end-walk'),
    path('walk-report/<int:pk>/', views.walk_report, name='walk-report'),
    path('walk-history/<int:pk>/', views.walk_history, name='walk-history'),
    path('get-calendar/', views.get_calendar, name='get-calendar'),
    path('update-walk-score/<int:pk>/', views.update_walk_score, name='update-walk-score'),
    
    #회원가입, 로그인, 로그아웃, 회원탈퇴
    path('signup/', views.user_create, name='user_create'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('delete/', views.user_delete, name='user_delete'),
    path('stats/<int:year>/<int:month>/', views.get_monthly_stats, name='get-monthly-stats'),
    path('calendar/<int:year>/<int:month>/', views.get_monthly_calendar, name='get-monthly-calendar'),

    # SRI 검사 결과 저장 및 불러오기
    path('sri/', views.sri_list_create, name='sri-list-create'),
    
    # 감정 기록 결과 저장 및 불러오기
    path('emotions/', views.emotion_list_create, name='emotion-list-create'),
    # 새로운 감정 분석
    path('analyze-emotion/', views.analyze_emotion, name='analyze-emotion'),
    # 새로운 감정 기록 저장
    path('save-emotion/', views.save_emotion, name='save-emotion'),
]
