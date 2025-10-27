from django.shortcuts import render
import random
import re
import requests
from drf_yasg import openapi    
from django.http import JsonResponse
from rest_framework import status, permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from knox.models import AuthToken
from knox.auth import TokenAuthentication
import random
import re
from django.http import JsonResponse
from rest_framework import status, permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from knox.models import AuthToken
from knox.auth import TokenAuthentication
from drf_yasg.utils import swagger_auto_schema
from .models import User
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


# Create your views here.
def split_name(full_name: str):
    parts = str(full_name).strip().split()
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        return parts[0], " ".join(parts[1:])
    
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

class RegisterAPI(GenericAPIView):
    serializer_class = RegisterSerialization

    @swagger_auto_schema(tags=['Authentication'])
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        country = request.data.get('country')
        referral_source = request.data.get('referral_source')
        source_known = request.data.get('source_known')

        if not email:
            return Response({'message': "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'message': "User already exists with this email! Please login"}, status=status.HTTP_400_BAD_REQUEST)

        # Password validation
        if password:
            checkpoint = password_check(password)
            if checkpoint == 1:
                return Response({'message': 'Password must contain at least one capital letter'}, status=status.HTTP_400_BAD_REQUEST)
            if checkpoint == 2:
                return Response({'message': 'Password must contain at least one digit'}, status=status.HTTP_400_BAD_REQUEST)
            if checkpoint == 3:
                return Response({'message': 'Password must contain at least one special character (@, $, #, &)'}, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        user = User.objects.create_user(
            username=email,  # still required by AbstractUser
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            country=country,
            source_known = source_known,
            referral_source=referral_source,
        )

        return Response(UserSerial(user).data, status=status.HTTP_201_CREATED)

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

        if user.check_password(password):
            token = AuthToken.objects.create(user)[1]  # Knox token
            user_data = {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'country': user.country,
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
        operation_description="Send a password reset link to a user's email address.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Registered user email address'),
            },
        ),
        responses={
            200: openapi.Response('Success', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={'message': openapi.Schema(type=openapi.TYPE_STRING)}
            )),
            404: "User not found",
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
        
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        domain = getattr(settings, "FRONTEND_URL", os.getenv("FRONTEND_URL", "https://quietly.tools"))
        domain = domain.rstrip("/")  # Remove trailing slash if any
        reset_link = f"{domain}/reset-password/{uid}/{token}/"
        # reset_link = f"{request.scheme}://{request.get_host()}/v1/api/reset-password/{uid}/{token}/"

        context = {'user': user, 'reset_link': reset_link}
        html_content = render_to_string('email/reset_password.html', context)
        text_content = f"Reset your password using this link: {reset_link}"

        msg = EmailMultiAlternatives("Reset Your Password", text_content, settings.DEFAULT_FROM_EMAIL, [email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return Response({"message": "Password reset email sent successfully!"}, status=status.HTTP_200_OK)


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

        user.set_password(password)
        user.save()
        return Response({"message": "Password has been reset successfully!"}, status=status.HTTP_200_OK)
    
class TestEmailAPI(APIView):
    """
    Send a test email to verify email configuration.
    """

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Email context
        context = {
            'user': {'first_name': 'Tester'},
            'message': 'This is a test email to verify your email configuration.',
        }

        # Load HTML template (optional)
        html_content = render_to_string('email/test_email.html', context)
        text_content = "This is a test email to verify your email configuration."

        try:
            msg = EmailMultiAlternatives(
                subject="Test Email from Your Django App",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            return Response({"message": f"Test email sent successfully to {email}"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)