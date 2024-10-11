from django.contrib import admin
from .models import SRI, User, WalkHistory, Calendar
from django.utils import timezone

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
  list_display = ['username', 'nickname']

@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
  list_display = ['pk', 'user', 'year', 'month', 'day', 'walkfinished']

# WalkHistory 모델 등록을 위한 Admin 클래스
@admin.register(WalkHistory)
class WalkHistoryAdmin(admin.ModelAdmin):
    list_display = ['pk', 'calendar', 'start_time', 'end_time']  # 원하는 필드들 추가

# SRIAdmin 클래스 정의
@admin.register(SRI)
class SRIAdmin(admin.ModelAdmin):
    list_display = ['user', 'sri_score', 'sri_date', 'sri_needed_status']  # sri_needed_status 필드 추가

    def sri_needed_status(self, obj):
        # 지금까지의 산책 횟수 계산
        walk_count = WalkHistory.objects.filter(calendar__user=obj.user).count()

        # SRI 검사를 해야 할지 여부 판단
        sri_needed = (walk_count == 0) or (walk_count % 5 == 0)

        # 오늘 SRI 검사를 했는지 여부 확인
        today = timezone.now().date()
        today_sri_done = SRI.objects.filter(user=obj.user, sri_date__date=today).exists()

        if today_sri_done:
            sri_needed = False

        return sri_needed  # True 또는 False 반환

    sri_needed_status.short_description = 'SRI Needed'  # admin에서 보이는 필드 이름 설정