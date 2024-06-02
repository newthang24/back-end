from django.urls import path
from . import views

urlpatterns = [

    path('start-walk/', views.start_walk, name='start-walk'),
    path('end-walk/<int:pk>/', views.end_walk, name='end-walk'),
    path('walk-report/<int:pk>/', views.walk_report, name='walk-report'),
    path('walk-history/<int:pk>/', views.walk_history, name='walk-history'),
    path('get-calendar/', views.get_calendar, name='get-calendar'),
    path('update-walk-score/<int:pk>/', views.update_walk_score, name='update-walk-score'),
    path('signup/', views.user_create, name='user_create'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('delete/', views.user_delete, name='user_delete'),

]
