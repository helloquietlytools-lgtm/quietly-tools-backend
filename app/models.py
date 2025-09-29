
# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Extends the default Django User model with additional fields.
    The default User model already has:
    | id
    | password
    | last_login
    | is_superuser
    | username
    | first_name
    | last_name
    | email
    | is_staff
    | is_active
    | date_joined
    """

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] 

    email = models.EmailField(unique=True, null=False, blank=False)
    country = models.CharField(max_length=100, null=True, blank=True)
    referral_source = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.email
