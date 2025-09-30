from .views import *
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter


urlpatterns = [
    path('', index, name='welcome'),
    path('v1/api/register', RegisterAPI.as_view(), name='register'),
    path('v1/api/login', LoginAPI.as_view(), name='login'),
    path('v1/api/logout', LogOutAPI.as_view(), name='logout'),
    path('v1/api/google/login', GoogleLoginAPIView.as_view(), name='google-login'),
    path('v1/api/google/callback', GoogleCallbackAPIView.as_view(), name='google-callback'),
    path('v1/api/github/login/', GitHubLoginAPIView.as_view(), name='github-login'),
    path('v1/api/github/callback/', GitHubCallbackAPIView.as_view(), name='github-callback'),
]