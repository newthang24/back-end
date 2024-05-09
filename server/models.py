from django.db import models

# Create your models here.

class User(models.Model):
  username = models.CharField(max_length=150, unique=True)
  password = models.CharField(max_length=128)
  first_name = models.CharField(max_length=30, blank=True)
  last_name = models.CharField(max_length=150, blank=True)
  
class WalkHistory(models.Model):
  user_id = models.ForeignKey(User, on_delete=models.CASCADE)
  startTime = models.DateTimeField()
  endTime = models.DateTimeField()
  score = models.IntegerField()
  distance = models.IntegerField()
  course = models.CharField(max_length=1)
  emotionImg = models.ImageField()
  
class Question(models.Model):
  walkHistory_id = models.ForeignKey(WalkHistory, on_delete=models.CASCADE)
  dialog = models.TextField()
  
class Answer(models.Model):
  question_id = models.ForeignKey(Question, on_delete=models.CASCADE)
  comment = models.TextField()
  emotion = models.CharField(max_length=10)