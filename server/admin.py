from django.contrib import admin
from .models import SRI, User, WalkHistory, Calendar

admin.site.register(User)
admin.site.register(SRI)
admin.site.register(WalkHistory)
admin.site.register(Calendar)