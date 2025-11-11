from rest_framework import serializers
from app.models import User


class RegisterSerialization(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'email',
            'password'
        ]

class CommpleteProfileSerialization(serializers.ModelSerializer):
    # password = serializers.CharField(write_only=True, required=True)  

    class Meta:
        model = User
        fields = [
           'first_name',
            'last_name',
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
    

class MarkdownSaveSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_blank=True)
    chunk_hashes = serializers.ListField(child=serializers.CharField(max_length=64), required=False)
    marked_complete = serializers.BooleanField(default=False)

class VaultlessStoreSerializer(serializers.Serializer):
    domain = serializers.CharField()
    username = serializers.CharField()
    generated_len = serializers.IntegerField(min_value=1)
    has_mixed = serializers.BooleanField()

# ------- Today XP (UI “xpSyetem”) -------
class TodayActivitiesSerializer(serializers.Serializer):
    pomodoro = serializers.DictField(child=serializers.JSONField(), required=False)
    markdown = serializers.DictField(child=serializers.JSONField(), required=False)
    vaultless = serializers.DictField(child=serializers.JSONField(), required=False)
    circular = serializers.DictField(child=serializers.JSONField(), required=False)
    soul = serializers.DictField(child=serializers.JSONField(), required=False)

class XPTodaySerializer(serializers.Serializer):
    date = serializers.DateField()
    streak = serializers.IntegerField()
    tool_xp = serializers.IntegerField()
    streak_xp = serializers.IntegerField()
    milestone_bonus = serializers.IntegerField()
    final_total = serializers.IntegerField()
    activities = TodayActivitiesSerializer()
    tools_used = serializers.ListField(child=serializers.CharField())

# ------- History / heatmap -------
class XPDayItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    qualified = serializers.BooleanField()
    xp = serializers.IntegerField()

class XPHistoryResponseSerializer(serializers.Serializer):
    xp14 = serializers.IntegerField()
    days = XPDayItemSerializer(many=True)

# ------- Streak (Option B needs next milestone) -------
class NextMilestoneSerializer(serializers.Serializer):
    milestone = serializers.IntegerField()
    daysUntil = serializers.IntegerField()
    bonus = serializers.IntegerField()

class StreakTodayResponseSerializer(serializers.Serializer):
    streak = serializers.IntegerField()
    previous_streak = serializers.IntegerField()
    qualified_today = serializers.BooleanField()
    milestone_hit = serializers.BooleanField()
    next_milestone = NextMilestoneSerializer(allow_null=True)

# ------- Leaderboard (Option B: rich “you” + champions) -------
class HeatCellSerializer(serializers.Serializer):
    date = serializers.DateField()
    qualified = serializers.BooleanField()

class ChampionEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    streak = serializers.IntegerField()
    xp14 = serializers.IntegerField()
    rankScore = serializers.IntegerField()
    division = serializers.CharField()
    position = serializers.IntegerField()
    heatmap = HeatCellSerializer(many=True)

class LeaderboardMeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    streak = serializers.IntegerField()
    xp14 = serializers.IntegerField()
    rankScore = serializers.IntegerField()
    division = serializers.CharField()
    position = serializers.IntegerField()
    next_milestone = NextMilestoneSerializer(allow_null=True)
    today_xp = serializers.IntegerField()
    tool_breakdown = serializers.DictField(child=serializers.IntegerField())
    heatmap = HeatCellSerializer(many=True)

class LeaderboardResponseSerializer(serializers.Serializer):
    you = LeaderboardMeSerializer()
    champions = ChampionEntrySerializer(many=True)

