from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Project, Task, ChatRoom, Message

admin.site.register(User, UserAdmin)
admin.site.register(Project)
admin.site.register(Task)
admin.site.register(ChatRoom)
admin.site.register(Message)