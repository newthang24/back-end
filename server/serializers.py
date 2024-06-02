from rest_framework import serializers
from .models import WalkHistory, Calendar

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