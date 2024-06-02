from rest_framework import serializers
from .models import WalkHistory, Calendar, User, SRI


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = '__all__'

class WalkHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WalkHistory
        fields = '__all__'

class WalkHistoryEndSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalkHistory
        fields = ['end_time', 'stable_score', 'stable_loc', 'walk_score', 'distance']

class WalkReportSerializer(serializers.ModelSerializer):
    calendar = CalendarSerializer()
    actual_walk_time = serializers.SerializerMethodField()

    class Meta:
        model = WalkHistory
        fields = '__all__'

    def get_actual_walk_time(self, obj):
        if obj.end_time and obj.start_time:
            return obj.end_time - obj.start_time
        return None


class UserSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        user = User.objects.create_user(
            username = validated_data['username'],
            nickname = validated_data['nickname'],
            password = validated_data['password']
        )
        return user
    class Meta:
        model = User
        fields = ['username', 'nickname', 'password']

class SRISerializer(serializers.ModelSerializer):
    class Meta:
        model = SRI
        fields = ['id', 'user', 'sri_score', 'sri_date']
        read_only_fields = ['user', 'sri_date']

class EmotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = ['question', 'sentence', 'emotion_large', 'emotion_small']