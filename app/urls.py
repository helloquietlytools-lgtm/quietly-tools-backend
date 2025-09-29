from .views import *
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter


urlpatterns = [
    path('', index, name='welcome'),
    path('v1/api/register', RegisterAPI.as_view(), name='register'),
    path('v1/api/login', LoginAPI.as_view(), name='login'),
    path('v1/api/logout', LogOutAPI.as_view(), name='logout'),
]