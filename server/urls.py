from django.urls import path, include
from . import views
from rest_framework import urls
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns =[
    path('signup/', views.UserCreate.as_view()),
    path('api-auth/', include('rest_framework.urls')),
    path('login/', obtain_auth_token, name='api_token_auth'),
]