from django.db import models

# Create your models here.

class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return self.username

class SRI(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sri_score = models.IntegerField()
    sri_date = models.DateTimeField()

    def __str__(self):
        return f"SRI Score: {self.sri_score} for {self.user.username}"

class Calendar(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    month = models.IntegerField()
    day = models.IntegerField()
    walkfinished = models.BooleanField(default=False)
    question = models.CharField(max_length=255, blank=True, null=True)
    sentence = models.CharField(max_length=255, blank=True, null=True)
    emotion_large = models.CharField(max_length=255, blank=True, null=True)
    emotion_small = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Calendar: {self.year}-{self.month}-{self.day} for {self.user.username}"

class WalkHistory(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    stable_score = models.FloatField()
    stable_loc = models.CharField(max_length=255)
    walk_score = models.FloatField()
    distance = models.IntegerField()
    course = models.CharField(max_length=255)

    def __str__(self):
        return f"Walk History: {self.start_time} to {self.end_time}"