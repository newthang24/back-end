from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UserManager(BaseUserManager):
    # 일반 user 생성
    def create_user(self, username, nickname, password=None):
        if not username:
            raise ValueError('must have user username')
        if not nickname:
            raise ValueError('must have user nickname')
        user = self.model(
            username = username,
            nickname = nickname
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    # 관리자 user 생성
    def create_superuser(self, username, nickname, password=None):
        user = self.create_user(
            username,
            password = password,
            nickname = nickname,
        )
        user.is_admin = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=10, null=False, blank=False, unique=True)
    nickname = models.CharField(max_length=10, blank=True)
    
    # User 모델의 필수 field
    is_active = models.BooleanField(default=True)    
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    # 헬퍼 클래스 사용
    objects = UserManager()

    # 사용자의 username field는 nickname으로 설정
    USERNAME_FIELD = 'username'
    # 필수로 작성해야하는 field
    REQUIRED_FIELDS = ['nickname']

    def __str__(self):
        return self.nickname
    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return self.is_admin

    @property
    def is_staff(self):
        return self.is_admin

class SRI(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sri_score = models.IntegerField()
    sri_date = models.DateTimeField()

    def __str__(self):
        return f"SRI Score: {self.sri_score} for {self.user.username}"

class Calendar(models.Model):
    #user = models.ForeignKey(User, on_delete=models.CASCADE)
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
        return f"Calendar: {self.year}-{self.month}-{self.day} for {self.user.username}"

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
        return f"Walk History: {self.start_time} to {self.end_time}"