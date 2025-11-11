
# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import UniqueConstraint, Index
from django.conf import settings

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
    source_known = models.CharField(max_length=500, null=True, blank=True)
    profile_completed = models.BooleanField(default=False)
    def __str__(self):
        return self.email
    
    
# ---------- Constants ----------
TOOL_CHOICES = [
    ("pomodoro", "Pomodoro"),
    ("markdown", "Markdown"),
    ("vaultless", "Vaultless"),
    ("circular", "Circular"),
    ("soul", "Soul"),
]
EVENT_KIND = [
    ("tool_xp", "Tool XP"),
    ("combo_xp", "Combo XP"),
    ("streak_xp", "Streak XP"),
    ("milestone_xp", "Milestone XP"),
]

MILESTONES = [7, 30, 100, 365]
MILESTONE_XP = {7: 100, 30: 300, 100: 1000, 365: 3000}
GLOBAL_TOOL_CAP = 600
PER_TOOL_CAP = {"pomodoro": 200, "markdown": 150, "vaultless": 100, "circular": 180, "soul": 80}

# ---------- Daily rollup ----------
class DailyXP(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="daily_xp")
    day = models.DateField(db_index=True)  # local day in settings.QUIETLY_TZ

    # per-tool buckets after per-tool caps
    pomodoro_xp = models.IntegerField(default=0)
    markdown_xp = models.IntegerField(default=0)
    vaultless_xp = models.IntegerField(default=0)
    circular_xp = models.IntegerField(default=0)
    soul_xp = models.IntegerField(default=0)
    combo_xp = models.IntegerField(default=0)

    # totals
    tool_xp_capped = models.IntegerField(default=0)   # min(sum(tool+combo), 600)
    streak_xp = models.IntegerField(default=0)        # outside 600
    milestone_xp = models.IntegerField(default=0)     # outside 600
    final_total_xp = models.IntegerField(default=0)   # tool_xp_capped + streak + milestone

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "day"], name="uq_dailyxp_user_day")]
        indexes = [Index(fields=["user", "day"])]

# ---------- Streak ----------
class Streak(models.Model):
    user = models.OneToOneField("User", on_delete=models.CASCADE, related_name="streak")
    current = models.PositiveIntegerField(default=0)
    longest = models.PositiveIntegerField(default=0)
    last_qualified_day = models.DateField(null=True, blank=True)
    timezone_name = models.CharField(max_length=64, default=getattr(settings, "QUIETLY_TZ", "Asia/Kolkata"))
    last_streak_save_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [Index(fields=["user"])]

# ---------- Milestone hits (once per length) ----------
class MilestoneHit(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="milestones")
    day = models.DateField()
    streak_len = models.PositiveIntegerField()
    xp_awarded = models.IntegerField()

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "streak_len"], name="uq_milestone_once")]
        indexes = [Index(fields=["user", "streak_len"])]

# ---------- Event ledger ----------
class XPEvent(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="xp_events")
    created_at = models.DateTimeField(auto_now_add=True)
    local_day = models.DateField(db_index=True)
    tool = models.CharField(max_length=16, choices=TOOL_CHOICES, null=True, blank=True)
    kind = models.CharField(max_length=16, choices=EVENT_KIND)
    points = models.IntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            Index(fields=["user", "local_day"]),
            Index(fields=["user", "tool", "local_day"]),
        ]

# ---------- Anti-cheat aids ----------
class MarkdownChunk(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="markdown_chunks")
    local_day = models.DateField(db_index=True)
    chunk_hash = models.CharField(max_length=64, db_index=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "local_day", "chunk_hash"], name="uq_md_chunk_once_per_day")]

class VaultlessDomain(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="vaultless_domains")
    local_day = models.DateField(db_index=True)
    fingerprint = models.CharField(max_length=128, db_index=True)  # domain|username

    class Meta:
        constraints = [UniqueConstraint(fields=["user", "local_day", "fingerprint"], name="uq_vaultless_domain_day_once")]

