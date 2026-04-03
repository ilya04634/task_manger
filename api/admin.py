from django.contrib import admin
from .models import User, Project, Task, ChatRoom, Message, FCMDeviceToken, TaskAttachment

# Регистрируем наши модели в админке
admin.site.register(User)
admin.site.register(Project)
admin.site.register(Task)
admin.site.register(ChatRoom)
admin.site.register(Message)
admin.site.register(FCMDeviceToken)
admin.site.register(TaskAttachment)