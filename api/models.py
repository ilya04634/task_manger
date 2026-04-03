from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta


class User(AbstractUser):
    ROLE_CHOICES = (
        ('USER', 'Пользователь'),
        ('MODERATOR', 'Модератор'),
    )
    # Глобальная роль юзера в приложении
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='USER')

    friends = models.ManyToManyField('self', blank=True, symmetrical=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return self.username


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Теперь админов может быть несколько.
    admins = models.ManyToManyField(User, related_name='administered_projects')
    # Участники проекта (админы тоже должны сюда входить для удобства)
    members = models.ManyToManyField(User, related_name='projects')

    def __str__(self):
        return self.name


class Task(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Низкий'),
        ('MED', 'Средний'),
        ('HIGH', 'Высокий'),
    )

    STATUS_CHOICES = (
        ('TODO', 'К выполнению'),
        ('IN_PROGRESS', 'В процессе'),
        ('DONE', 'Готово'),
    )

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='TODO')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    importance = models.CharField(max_length=4, choices=PRIORITY_CHOICES, default='MED')
    estimated_time = models.DurationField(default=timedelta(hours=1))

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='assigned_tasks', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)


class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('PROJECT', 'Проектный'),
        ('PERSONAL', 'Личный'),
    )
    type = models.CharField(max_length=10, choices=ROOM_TYPES)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, null=True, blank=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class FCMDeviceToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)