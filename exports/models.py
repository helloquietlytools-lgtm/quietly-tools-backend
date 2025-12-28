from django.db import models
from app.models import User

class OAuthToken(models.Model):
    PROVIDERS = [
        ("gdrive", "Google Drive"),
        ("github", "GitHub"),
        ("dropbox", "Dropbox"),
        ("box", "Box"),
        ("onedrive", "OneDrive"),
        ("medium", "Medium"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "provider")
