from rest_framework import serializers
from app.models import User


class RegisterSerialization(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'password',
            'country',
            'source_known',
            'referral_source',
        ]


class LoginSerialization(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class LogOutSerializer(serializers.Serializer):
    pass


class UserSerial(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'country',
            'source_known',
            'referral_source',
            'is_active',
            'is_staff',
        ]

class GoogleLoginURLSerializer(serializers.Serializer):
    auth_url = serializers.URLField()

class GoogleLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=True)
    is_mobile = serializers.BooleanField(default=False)

class GitHubAuthSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField(required=False)



class TestEmailSerialization(serializers.Serializer):
    email = serializers.EmailField(required=True)

