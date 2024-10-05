from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, username, nickname, password=None):
        if not username:
            raise ValueError('The Username field must be set')
        if not nickname:
            raise ValueError('The Nickname field must be set')
        user = self.model(
            username=username,
            nickname=nickname
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, nickname, password=None):
        user = self.create_user(
            username=username,
            nickname=nickname,
            password=password,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=10, unique=True)
    nickname = models.CharField(max_length=10, blank=True)

    level = models.IntegerField(default=1)
    points = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nickname']

    def __str__(self):
        return self.nickname

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    def add_points(self, points):
        self.points += points
        self.check_level_up()
        self.save()

    def check_level_up(self):
        level_thresholds = {
            1: 100,
            # 2: 200,
            # 3: 300,
            # 4: 400,
            # 5: 500,
            # Add more levels and their thresholds as needed
        }
        # 현재 레벨이 임계값에 도달할 때마다 레벨을 올리고 포인트를 0으로 초기화
        while self.points >= 100:
            self.level += 1
            self.points -= 100  # 레벨업 후 포인트를 0으로 초기화

class SRI(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sri_score = models.IntegerField()
    sri_date = models.DateTimeField()

    def __str__(self):
        return f"SRI Score: {self.sri_score} for {self.user.username}"

class Calendar(models.Model):

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    # user 부분 주석 풀 때 null=True 임시로 해 주고 데이터 채운 뒤 변경해야 함

    year = models.IntegerField()
    month = models.IntegerField()
    day = models.IntegerField()
    walkfinished = models.BooleanField(default=False)
    # 감정 관련 model
    question = models.CharField(max_length=255, blank=True, null=True)
    sentence = models.CharField(max_length=255, blank=True, null=True)
    emotion_large = models.CharField(max_length=255, blank=True, null=True)
    emotion_small = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        if self.user:
            return f"Calendar[{self.pk}]: {self.year}-{self.month}-{self.day} for {self.user.username}"
        else:
            return f"Calendar[{self.pk}]: {self.year}-{self.month}-{self.day} (No User)"

class WalkHistory(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    stable_score = models.FloatField(null=True, blank=True)
    stable_loc = models.CharField(max_length=255,null=True, blank=True)
    walk_score = models.FloatField(null=True, blank=True)
    distance = models.IntegerField(null=True, blank=True)
    course = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Walk History Id: {self.pk} / {self.start_time} ~ {self.end_time}"