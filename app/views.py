from django.shortcuts import render
import random
from datetime import timedelta
from zoneinfo import ZoneInfo
import  os, re, logging
import requests
from random import sample
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from drf_yasg import openapi    
from django.http import JsonResponse
from rest_framework import status, permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from knox.models import AuthToken
from knox.auth import TokenAuthentication
import random
from django.utils.encoding import force_str
from rest_framework.permissions import IsAuthenticated
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.http import JsonResponse
from rest_framework import status, permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from knox.models import AuthToken
from knox.auth import TokenAuthentication
from drf_yasg.utils import swagger_auto_schema
from .models import (
    User, DailyXP, Streak, XPEvent, MarkdownChunk, VaultlessDomain,
    MILESTONES, MILESTONE_XP, PER_TOOL_CAP, GLOBAL_TOOL_CAP
)
from .serialization import *
from django.conf import settings
from rest_framework import viewsets
from django.utils.crypto import get_random_string
from rest_framework.views import APIView
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os
from django.core.mail import send_mail
from asgiref.sync import sync_to_async
import logging, threading

logger = logging.getLogger(__name__)
QUIETLY_TZ = ZoneInfo(getattr(settings, "QUIETLY_TZ", "Asia/Kolkata"))
# Create your views here.
def split_name(full_name: str):
    parts = str(full_name).strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return parts[0], " ".join(parts[1:])


def _local_day(dt): 
    return dt.astimezone(QUIETLY_TZ).date()

def _get_or_create_daily(user, day):
    obj, _ = DailyXP.objects.get_or_create(user=user, day=day)
    return obj

def _tools_used_today(user, day):
    names = set()
    ev = XPEvent.objects.filter(user=user, local_day=day, kind="tool_xp").values_list("tool", flat=True)
    for t in ev:
        if t:
            names.add(t)
    return names

def _apply_tool_cap(tool, before):
    return min(before, PER_TOOL_CAP[tool])

def _recompute_totals(d: DailyXP):
    subtotal = d.pomodoro_xp + d.markdown_xp + d.vaultless_xp + d.circular_xp + d.soul_xp + d.combo_xp
    d.tool_xp_capped = min(subtotal, GLOBAL_TOOL_CAP)
    d.final_total_xp = d.tool_xp_capped + d.streak_xp + d.milestone_xp

def _division(streak:int, xp14:int):
    # matches your UI config (xpSyetem.js)  :contentReference[oaicite:0]{index=0}
    if streak >= 100 and xp14 >= 4000: return "Monk"
    if streak >= 30 and xp14 >= 1500: return "Gold"
    if streak >= 7 and xp14 >= 500:   return "Silver"
    return "Bronze"

def _rankscore(xp14:int, streak_xp_sum_14:int):
    # xpSyetem.js: xp14 + 5 * avgDailyStreakXP  (avg over 14d)
    return int(xp14 + 5 * (streak_xp_sum_14 / 14.0))

def _next_milestone(streak:int):
    for m in MILESTONES:
        if streak < m:
            return {"milestone": m, "daysUntil": m - streak, "bonus": MILESTONE_XP[m]}
    return None 
def password_check(passwd):
    flag = 0
    import re
    if not re.search("[A-Z]", passwd):
        flag = 1
    if not re.search("[0-9]", passwd):
        flag = 2
    if not re.search("[@$!%*#?&]", passwd):
        flag = 3
    return flag

def index(request):
    return JsonResponse({"Message": "Welcome to the Quietly Project"})

# class RegisterAPI(GenericAPIView):
#     serializer_class = RegisterSerialization

#     @swagger_auto_schema(tags=['Authentication'])
#     def post(self, request, *args, **kwargs):
#         email = request.data.get('email')
#         password = request.data.get('password')
#         first_name = request.data.get('first_name')
#         last_name = request.data.get('last_name')
#         country = request.data.get('country')
#         referral_source = request.data.get('referral_source')
#         source_known = request.data.get('source_known')

#         if not email:
#             return Response({'message': "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

#         if User.objects.filter(email=email).exists():
#             return Response({'message': "User already exists with this email! Please login"}, status=status.HTTP_400_BAD_REQUEST)

#         # Password validation
#         if password:
#             checkpoint = password_check(password)
#             if checkpoint == 1:
#                 return Response({'message': 'Need Strong Password'}, status=status.HTTP_400_BAD_REQUEST)
#             if checkpoint == 2:
#                 return Response({'message': 'Need Strong Password'}, status=status.HTTP_400_BAD_REQUEST)
#             if checkpoint == 3:
#                 return Response({'message': 'Need Strong Password'}, status=status.HTTP_400_BAD_REQUEST)

#         # Create user
#         user = User.objects.create_user(
#             username=email,  # still required by AbstractUser
#             email=email,
#             password=password,
#             first_name=first_name,
#             last_name=last_name,
#             country=country,
#             source_known = source_known,
#             referral_source=referral_source,
#             is_active = False
#         )
#         uid = urlsafe_base64_encode(force_bytes(user.pk))
#         token = default_token_generator.make_token(user)
#         domain = getattr(settings, "FRONTEND_URL", os.getenv("FRONTEND_URL", "https://quietly.tools"))
#         domain = domain.rstrip("/")
#         verify_link = f"{domain}/verify-email/{uid}/{token}/"

#         # Render email template
#         context = {"user": user, "verify_link": verify_link}
#         html_content = render_to_string("email/verify_email.html", context)
#         text_content = f"Please verify your email: {verify_link}"

#         # Prepare SendGrid email
#         sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", "hello@quietly.tools")
#         sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

#         if not sendgrid_api_key:
#             return Response({"error": "SendGrid API key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         message = Mail(
#             from_email=f"Quietly Tools <{sender_email}>",
#             to_emails=user.email,
#             subject="✅ Verify Your Email - Quietly Tools",
#             plain_text_content=text_content,
#             html_content=html_content,
#         )

#         # Send via SendGrid
#         try:
#             sg = SendGridAPIClient(sendgrid_api_key)
#             response = sg.send(message)
#             if response.status_code in [200, 202]:
#                 return Response(
#                     {"message": "Registration successful! Please verify your email to activate your account."},
#                     status=status.HTTP_201_CREATED
#                 )
#             else:
#                 return Response(
#                     {"error": f"SendGrid failed with status {response.status_code}", "details": response.body.decode()},
#                     status=status.HTTP_500_INTERNAL_SERVER_ERROR
#                 )
#         except Exception as e:
#             print("SendGrid Error:", str(e))
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegisterAPI(GenericAPIView):
    serializer_class = RegisterSerialization

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email:
            return Response({'message': "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'message': "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'message': "User already exists with this email! Please login"}, status=status.HTTP_400_BAD_REQUEST)

        # Password validation
        checkpoint = password_check(password)
        if checkpoint in [1, 2, 3]:
            return Response({'message': 'Need Strong Password'}, status=status.HTTP_400_BAD_REQUEST)

        # Create inactive user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            is_active=False
        )

        # Generate email verification link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        domain = getattr(settings, "FRONTEND_URL", os.getenv("FRONTEND_URL", "https://quietly.tools")).rstrip("/")
        verify_link = f"{domain}/verify-email/{uid}/{token}/"

        # Send email
        context = {"user": user, "verify_link": verify_link}
        html_content = render_to_string("email/verify_email.html", context)
        text_content = f"Please verify your email: {verify_link}"

        sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", "hello@quietly.tools")
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

        if not sendgrid_api_key:
            return Response({"error": "SendGrid API key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        message = Mail(
            from_email=f"Quietly Tools <{sender_email}>",
            to_emails=user.email,
            subject="✅ Verify Your Email - Quietly Tools",
            plain_text_content=text_content,
            html_content=html_content,
        )

        try:
            sg = SendGridAPIClient(sendgrid_api_key)
            response = sg.send(message)
            if response.status_code in [200, 202]:
                return Response(
                    {"message": "Registration successful! Please verify your email to activate your account."},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"error": f"SendGrid failed with status {response.status_code}", "details": response.body.decode()},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            print("SendGrid Error:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompleteProfileAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommpleteProfileSerialization
    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request, *args, **kwargs):
        user = request.user
        if not user.is_active:
            return Response({"message": "Email not verified yet!"}, status=status.HTTP_403_FORBIDDEN)

        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        country = request.data.get('country')
        referral_source = request.data.get('referral_source')
        source_known = request.data.get('source_known')

        # Validate required fields (optional)
        if not first_name or not last_name:
            return Response({"message": "First name and last name are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Update user   
        user.first_name = first_name
        user.last_name = last_name
        user.country = country
        user.referral_source = referral_source
        user.source_known = source_known
        user.profile_completed = True  # Optional flag
        user.save()

        return Response({"message": "Profile completed successfully!"}, status=status.HTTP_200_OK)

class VerifyEmailAPI(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"error": "Invalid verification link"}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({"message": "Email already verified!"}, status=status.HTTP_200_OK)

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"message": "Email verified successfully! You can now log in."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Verification link expired or invalid"}, status=status.HTTP_400_BAD_REQUEST)


class LoginAPI(GenericAPIView):
    serializer_class = LoginSerialization

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"message": "Email and Password are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': "User does not exist!"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not user.is_active:
            return Response({"message": "Please verify your email before login with yur password."}, status=status.HTTP_403_FORBIDDEN)

        if user.check_password(password):
            token = AuthToken.objects.create(user)[1]  # Knox token
            user_data = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'country': user.country,
                'is_completed':user.profile_completed
            }
            result = {'token': token, **user_data}
            return JsonResponse({'status': 'Success', 'message': 'You have signed in successfully!', 'data': result}, safe=False)

        return Response({"message": "Invalid Email or Password!"}, status=status.HTTP_400_BAD_REQUEST)
    
class LogOutAPI(GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (TokenAuthentication,)
    serializer_class = LogOutSerializer

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request, *args, **kwargs):
        AuthToken.objects.filter(user=request.user).delete()
        return Response({"message": "Logout Successfully!"})
    
class GoogleLoginAPIView(GenericAPIView):
    serializer_class = GoogleLoginURLSerializer
    filter_backends = []


    @swagger_auto_schema(tags=['Authentication'], responses={200: GoogleLoginURLSerializer})
    def get(self, request):
        if getattr(self, 'swagger_fake_view', False):
            return Response({'auth_url': 'https://example.com'})

        scope = "https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email"
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&access_type=offline"
            f"&prompt=select_account"
        )
        return Response({'auth_url': auth_url})

class GoogleCallbackAPIView(GenericAPIView):
    serializer_class = GoogleLoginSerializer

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        code = request.data.get('access_token')
        is_mobile = request.data.get('is_mobile')
        if not code:
            return Response({'error': 'No code provided'}, status=status.HTTP_400_BAD_REQUEST)

        if is_mobile:
            userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            user_info_response = requests.get(userinfo_url, headers={"Authorization": f"Bearer {code}"})

            if user_info_response.status_code != 200:
                raise ValueError(f"Invalid access token. Status code: {user_info_response.status_code}")
        else:
            token_response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'code': code,
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                    'grant_type': 'authorization_code'
                }
            )

            token_data = token_response.json()
            access_token = token_data.get('access_token')
            if not access_token:
                return Response({'error': 'Failed to retrieve access token'}, status=status.HTTP_400_BAD_REQUEST)

            # Step 2: Get user info
            user_info_response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )

        user_info = user_info_response.json()
        print(user_info)

        email = user_info.get('email')
        if not email:
            return Response({'error': 'Email not found in Google response'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            first_name, last_name = split_name(user_info.get('name'))
            # If user does not exist, create a new user
            user = User.objects.create_user(
                username=email,
                email=email,
                password=get_random_string(length=12),
                first_name=first_name,
                last_name=last_name
            )
        token = AuthToken.objects.create(user)[1]
        user_data = UserSerial(user).data
        result = {
            'token': token,
            **user_data
        }
        return JsonResponse(result, safe=False)
class EmptySerializer(serializers.Serializer):
    pass 
class GitHubLoginAPIView(GenericAPIView):
    """Return GitHub login URL with client_id"""
    # serializer_class = None
    serializer_class = EmptySerializer
    filter_backends = []

    @swagger_auto_schema(
        tags=['Authentication'],
        request_body=None,   # ✅ ensures no body is expected
        operation_description="Get GitHub OAuth login URL"
    )
    def get(self, request):
        github_url = (
            f"{settings.GITHUB_AUTH_URL}"
            f"?client_id={settings.GITHUB_CLIENT_ID}"
            f"&scope=read:user user:email"
        )
        return Response({"auth_url": github_url})


class GitHubCallbackAPIView(GenericAPIView):
    serializer_class = GitHubAuthSerializer

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"error": "No code provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Step 1: Exchange code for GitHub access token
        token_res = requests.post(
            settings.GITHUB_TOKEN_URL,
            headers={'Accept': 'application/json'},
            data={
                'client_id': settings.GITHUB_CLIENT_ID,
                'client_secret': settings.GITHUB_CLIENT_SECRET,
                'code': code,
            }
        )
        token_json = token_res.json()
        access_token = token_json.get("access_token")

        if not access_token:
            return Response({"error": "Failed to fetch GitHub access token"}, status=status.HTTP_400_BAD_REQUEST)

        # Step 2: Get user info from GitHub
        user_res = requests.get(
            settings.GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_res.json()


        username = user_info.get("login")
        email = user_info.get("email") or f"{username}@github.local"
        name = user_info.get("name") or username
        
        if not username:
            return Response({"error": "Username not found in GitHub response"}, status=status.HTTP_400_BAD_REQUEST)

        # Step 3: Get or create user
        user = User.objects.filter(email=email).first()
        if not user:
            first_name, last_name = split_name(name)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=get_random_string(length=12),
                first_name=first_name,
                last_name=last_name
            )

        # Step 4: Create Knox token (same as Google login flow)
        token = AuthToken.objects.create(user)[1]
        user_data = UserSerial(user).data

        result = {
            "token": token,
            **user_data
        }
        return JsonResponse(result, safe=False)
    
#forgot password view
class ForgotPasswordAPI(APIView):
    @swagger_auto_schema(
        tags=['Authentication'],
        operation_description="Send a password reset link to a user's registered email address using SendGrid.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Registered user email address'
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description='Password reset email sent successfully.',
                examples={
                    "application/json": {"message": "Password reset email sent successfully!"}
                }
            ),
            404: openapi.Response(
                description='User not found.',
                examples={
                    "application/json": {"error": "No account found with that email"}
                }
            ),
            500: openapi.Response(
                description='SendGrid error.',
                examples={
                    "application/json": {"error": "SendGridException: Invalid API key"}
                }
            ),
        },
    )
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "No account found with that email"}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate token & reset link
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        domain = getattr(settings, "FRONTEND_URL", os.getenv("FRONTEND_URL", "https://quietly.tools"))
        domain = domain.rstrip("/")  # ensure no trailing slash
        reset_link = f"{domain}/reset-password/{uid}/{token}/"

        # Prepare email content
        context = {"user": user, "reset_link": reset_link}
        html_content = render_to_string("email/reset_password.html", context)
        text_content = f"Reset your password using this link: {reset_link}"

        sender_email = getattr(settings, "DEFAULT_FROM_EMAIL", "hello@quietly.tools")
        sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

        if not sendgrid_api_key:
            return Response({"error": "SendGrid API key not configured."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Create SendGrid mail
        message = Mail(
            from_email=f"Quietly Tools <{sender_email}>",
            to_emails=email,
            subject="🔐 Reset Your Password - Quietly Tools",
            plain_text_content=text_content,
            html_content=html_content,
        )

        # Send mail using SendGrid
        try:
            sg = SendGridAPIClient(sendgrid_api_key)
            response = sg.send(message)
            if response.status_code in [200, 202]:
                return Response({"message": "Password reset email sent successfully!"}, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": f"SendGrid failed with status {response.status_code}",
                    "details": response.body.decode()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            print("SendGrid Error:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)      


class ResetPasswordAPI(APIView):
    @swagger_auto_schema(
        operation_description="Reset user password using the tokenized link received via email.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['password'],
            properties={
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='New password'),
            },
        ),
        responses={
            200: openapi.Response('Password reset successful'),
            400: "Invalid token or request",
        },
    )
    def post(self, request, uidb64, token):
       
        password = request.data.get('password')
        if not password:
            return Response({"error": "Password is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid link"}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Check if the new password matches the old password
        if user.check_password(password):
            return Response(
                {"error": "New password cannot be the same as the previous password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(password)
        user.save()

        return Response(
            {"message": "Password has been reset successfully!"},
            status=status.HTTP_200_OK
        )

# @method_decorator(csrf_exempt, name='dispatch')
class TestEmailAPI(APIView):
    """
    Send a test email using SendGrid API.
    """

    @swagger_auto_schema(
        tags=['Email'],
        operation_description="Send a test email using SendGrid to verify configuration.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],     
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_EMAIL,
                    description='Recipient email address to send the test email to.'
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Email sent successfully.",
                examples={
                    "application/json": {"message": "✅ Email sent successfully to example@example.com"}
                },
            ),
            400: openapi.Response(
                description="Missing email field.",
                examples={
                    "application/json": {"error": "Email is required"}
                },
            ),
            500: openapi.Response(
                description="SendGrid API or sending error.",
                examples={
                    "application/json": {"error": "SendGridException: Invalid API key"}
                },
            ),
        }
    )
    @csrf_exempt
    def post(self, request):
        recipient_email = request.data.get('email')
        if not recipient_email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        sender_email = "hello@quietly.tools"  # This must be verified in your SendGrid account
        api_key = os.getenv("SENDGRID_API_KEY")

        if not api_key:
            return Response({"error": "Missing SENDGRID_API_KEY in environment"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        message = Mail(
            from_email=f"Quietly <{sender_email}>",
            to_emails=recipient_email,
            subject="✅ Test Email via SendGrid",
            html_content="""
                <div style="font-family:Arial, sans-serif;">
                    <h3>🚀 SendGrid Test Email</h3>
                    <p>This is a test email sent from <b>Quietly</b> using SendGrid API.</p>
                </div>
            """
        )

        try:
            sg = SendGridAPIClient(api_key)
            response = sg.send(message)
            return Response({
                "message": f"✅ Email sent successfully to {recipient_email}",
                "status_code": response.status_code
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
# ----------------- streak core -----------------
@transaction.atomic
def _qualify_and_award_streak(user, now=None):
    now = now or timezone.now()
    day = _local_day(now)
    s, _ = Streak.objects.get_or_create(user=user)

    previous = s.current
    if s.last_qualified_day == day:
        d = _get_or_create_daily(user, day)
        return {
            "streak": s.current,
            "previous_streak": previous,
            "qualified_today": True,
            "milestone_hit": d.milestone_xp > 0,
            "next_milestone": _next_milestone(s.current),
        }

    if s.last_qualified_day == day - timedelta(days=1):
        s.current += 1
    else:
        s.current = 1
    s.longest = max(s.longest, s.current)
    s.last_qualified_day = day
    s.save()

    d = _get_or_create_daily(user, day)
    d.streak_xp = min(s.current, 50) * 10  # outside 600
    # milestone
    milestone_today = 0
    if s.current in MILESTONES:
        from .models import MilestoneHit
        hit, created = MilestoneHit.objects.get_or_create(
            user=user, streak_len=s.current,
            defaults={"day": day, "xp_awarded": MILESTONE_XP[s.current]}
        )
        if created:
            milestone_today = MILESTONE_XP[s.current]
            d.milestone_xp = milestone_today

    _recompute_totals(d)
    d.save()
    return {
        "streak": s.current,
        "previous_streak": previous,
        "qualified_today": True,
        "milestone_hit": milestone_today > 0,
        "next_milestone": _next_milestone(s.current),
    }

# ----------------- tool actions (Markdown, Vaultless) -----------------
class MarkdownSaveAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MarkdownSaveSerializer
    @swagger_auto_schema(tags=['Tool: Markdown'])
    def post(self, request):
        s = self.serializer_class(data=request.data); s.is_valid(raise_exception=True)
        now = timezone.now(); day = _local_day(now)
        d = _get_or_create_daily(request.user, day)

        # first save bonus once
        if d.markdown_xp == 0:
            d.markdown_xp = _apply_tool_cap("markdown", d.markdown_xp + 20)
            XPEvent.objects.create(user=request.user, local_day=day, kind="tool_xp", tool="markdown", points=20, meta={"first_save": True})

        # chunk hashes give +1 per 100 chars. We credit 250 per new chunk (server-side dedup)
        gained_chars = 0
        for h in s.validated_data.get("chunk_hashes") or []:
            obj, created = MarkdownChunk.objects.get_or_create(user=request.user, local_day=day, chunk_hash=h)
            if created: gained_chars += 250
        pts_chars = gained_chars // 100
        if pts_chars:
            d.markdown_xp = _apply_tool_cap("markdown", d.markdown_xp + pts_chars)
            XPEvent.objects.create(user=request.user, local_day=day, kind="tool_xp", tool="markdown", points=pts_chars, meta={"new_chars": gained_chars})

        if s.validated_data.get("marked_complete", False):
            d.markdown_xp = _apply_tool_cap("markdown", d.markdown_xp + 30)
            XPEvent.objects.create(user=request.user, local_day=day, kind="tool_xp", tool="markdown", points=30, meta={"marked_complete": True})

        # recompute combos + totals
        used = _tools_used_today(request.user, day)
        if len(used) >= 3: d.combo_xp = 60
        if len(used) == 5: d.combo_xp = 200
        _recompute_totals(d); d.save()

        # qualify streak
        _qualify_and_award_streak(request.user, now=now)
        return Response({"message": "Markdown logged"}, status=200)

class VaultlessStoreAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VaultlessStoreSerializer
    @swagger_auto_schema(tags=['Tool: Vaultless'])
    def post(self, request):
        s = self.serializer_class(data=request.data); s.is_valid(raise_exception=True)
        now = timezone.now(); day = _local_day(now)
        d = _get_or_create_daily(request.user, day)

        # max 2 rewarded domains/day
        if VaultlessDomain.objects.filter(user=request.user, local_day=day).count() < 2:
            fp = f"{s.validated_data['domain']}|{s.validated_data['username']}".lower()
            VaultlessDomain.objects.get_or_create(user=request.user, local_day=day, fingerprint=fp)
            # 20 generate + 30 store
            pts = 20 if (s.validated_data["generated_len"] >= 16 and s.validated_data["has_mixed"]) else 0
            if pts:
                add = pts + 30
                d.vaultless_xp = _apply_tool_cap("vaultless", d.vaultless_xp + add)
                XPEvent.objects.create(user=request.user, local_day=day, kind="tool_xp", tool="vaultless", points=add, meta={"domain": s.validated_data["domain"]})

        # recompute combos + totals
        used = _tools_used_today(request.user, day)
        if len(used) >= 3: d.combo_xp = 60
        if len(used) == 5: d.combo_xp = 200
        _recompute_totals(d); d.save()

        _qualify_and_award_streak(request.user, now=now)
        return Response({"logged": True}, status=200)

# ----------------- streak + xp summaries -----------------
class StreakQualifyTodayAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(tags=['Streak'])
    def post(self, request):
        data = _qualify_and_award_streak(request.user)
        return Response(StreakTodayResponseSerializer(data).data, status=200)

class StreakTodayAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(tags=['Streak'])
    def get(self, request):
        # idempotent: returns today's state
        data = _qualify_and_award_streak(request.user)
        return Response(StreakTodayResponseSerializer(data).data, status=200)

class XPTodayAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(tags=['XP'])
    def get(self, request):
        now = timezone.now(); day = _local_day(now)
        d = _get_or_create_daily(request.user, day)
        used = list(_tools_used_today(request.user, day))
        payload = {
            "date": day,
            "streak": (request.user.streak.current if hasattr(request.user, "streak") else 0),
            "tool_xp": d.tool_xp_capped,
            "streak_xp": d.streak_xp,
            "milestone_bonus": d.milestone_xp,
            "final_total": d.final_total_xp,
            "activities": {
                # front-end can compute visuals; we only expose minimal booleans/ints
                "pomodoro": {},
                "markdown": {},
                "vaultless": {},
                "circular": {},
                "soul": {},
            },
            "tools_used": used
        }
        return Response(XPTodaySerializer(payload).data, status=200)

class XPHistoryAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(tags=['XP'])
    def get(self, request):
        days = int(request.query_params.get("days", 14))
        today = _local_day(timezone.now())
        start = today - timedelta(days=days-1)
        rows = DailyXP.objects.filter(user=request.user, day__gte=start, day__lte=today).order_by("day")
        items = []
        xp14 = 0
        for d in rows:
            items.append({"date": d.day, "qualified": (d.streak_xp > 0), "xp": d.final_total_xp})
            xp14 += d.final_total_xp
        payload = {"xp14": xp14, "days": items}
        return Response(XPHistoryResponseSerializer(payload).data, status=200)

# ----------------- leaderboard (Option B) -----------------
class LeaderboardAPI(GenericAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=['Leaderboard'])
    def get(self, request):
        today = _local_day(timezone.now())
        start = today - timedelta(days=13)

        xp_sums = (
            DailyXP.objects
            .filter(day__gte=start, day__lte=today)
            .values("user_id")
            .annotate(xp14=Sum("final_total_xp"), streak14=Sum("streak_xp"))
        )
        sums_map = {r["user_id"]: (r["xp14"] or 0, r["streak14"] or 0) for r in xp_sums}
        user_ids = list(sums_map.keys())

        # ✅ Pull all users in last 14 days
        users = list(User.objects.filter(id__in=user_ids).only("id", "first_name", "last_name"))

        # ✅ Randomly sample up to 50 users (for leaderboard display)
        if len(users) > 50:
            users = sample(users, 50)

        champions = []
        for u in users:
            xp14, streak_sum = sums_map[u.id]
            streak = getattr(getattr(u, "streak", None), "current", 0)
            rs = _rankscore(xp14, streak_sum)
            division = _division(streak, xp14)

            days = DailyXP.objects.filter(user=u, day__gte=start, day__lte=today).order_by("day")
            heat = [{"date": row.day, "qualified": (row.streak_xp > 0)} for row in days]

            champions.append({
                "id": u.id,
                "name": (u.first_name or "") or "User",
                "streak": streak,
                "xp14": xp14,
                "rankScore": rs,
                "division": division,
                "position": 0,
                "heatmap": heat,
            })

        # sort and rank
        champions.sort(key=lambda x: (-x["streak"], -x["rankScore"]))
        for i, c in enumerate(champions, 1):
            c["position"] = i

        me = next((c for c in champions if c["id"] == request.user.id), None)
        if not me:
            streak = getattr(getattr(request.user, "streak", None), "current", 0)
            me = {
                "id": request.user.id,
                "name": (request.user.first_name or "") or "You",
                "streak": streak,
                "xp14": 0,
                "rankScore": _rankscore(0, 0),
                "division": _division(streak, 0),
                "position": len(champions) + 1,
                "heatmap": [],
            }

        today_row = DailyXP.objects.filter(user=request.user, day=today).first()
        tool_breakdown = {
            "pomodoro": getattr(today_row, "pomodoro_xp", 0) if today_row else 0,
            "markdown": getattr(today_row, "markdown_xp", 0) if today_row else 0,
            "vaultless": getattr(today_row, "vaultless_xp", 0) if today_row else 0,
            "circular": getattr(today_row, "circular_xp", 0) if today_row else 0,
            "soul": getattr(today_row, "soul_xp", 0) if today_row else 0,
        }

        me_rich = dict(me)
        me_rich.update({
            "next_milestone": _next_milestone(me["streak"]),
            "today_xp": getattr(today_row, "final_total_xp", 0) if today_row else 0,
            "tool_breakdown": tool_breakdown,
        })

        payload = {"you": me_rich, "champions": champions}
        return Response(LeaderboardResponseSerializer(payload).data, status=200)

