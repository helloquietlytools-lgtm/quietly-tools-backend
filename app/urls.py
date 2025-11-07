from .views import *
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter


urlpatterns = [
    # url for login
    path('', index, name='welcome'),
    path('v1/api/register', RegisterAPI.as_view(), name='register'),
    path('v1/api/complete_profile', CompleteProfileAPI.as_view(), name='complete_profile'),
    path('v1/api/login', LoginAPI.as_view(), name='login'),
    path('v1/api/logout', LogOutAPI.as_view(), name='logout'),
    path('v1/api/google/login', GoogleLoginAPIView.as_view(), name='google-login'),
    path('v1/api/google/callback', GoogleCallbackAPIView.as_view(), name='google-callback'),
    path('v1/api/github/login/', GitHubLoginAPIView.as_view(), name='github-login'),
    path('v1/api/github/callback/', GitHubCallbackAPIView.as_view(), name='github-callback'),
    path('v1/api/forgot-password', ForgotPasswordAPI.as_view(), name='forgot-password'),
    path('v1/api/reset-password/<uidb64>/<token>/', ResetPasswordAPI.as_view(), name='reset-password'),
    path('v1/api/test-email/', TestEmailAPI.as_view(), name='test-email'),
    path("v1/api/verify-email/<uidb64>/<token>/", VerifyEmailAPI.as_view(), name="verify-email"),
]