from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, Task
from .models import Project, Task, ChatRoom, Message
from .models import Project, Task, ChatRoom, Message, TaskAttachment


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'avatar', 'role']


class ProjectSerializer(serializers.ModelSerializer):
    admins = UserSerializer(many=True, read_only=True)
    members = UserSerializer(many=True, read_only=True)

    # Поля для добавления участников по ID при создании/обновлении
    admin_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='admins',
        many=True,
        write_only=True,
        required=False
    )
    member_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='members',
        many=True,
        write_only=True,
        required=False
    )

    # Новое поле: роль текущего залогиненного пользователя
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        # ВНИМАНИЕ СЮДА: my_role теперь в списке!
        fields = ['id', 'name', 'description', 'admins', 'admin_ids', 'members', 'member_ids', 'my_role']

    def get_my_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return "GUEST"

        user = request.user
        if user.role == 'MODERATOR' or user.is_superuser:
            return "GLOBAL_MODERATOR"
        if user in obj.admins.all():
            return "PROJECT_ADMIN"
        if user in obj.members.all():
            return "PROJECT_MEMBER"
        return "GUEST"
class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ['id', 'file', 'uploaded_at']


class TaskSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)


    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'importance', 'status',
            'estimated_time', 'project', 'creator', 'assignee', 'created_at',
            'attachments'
        ]
        read_only_fields = ['creator', 'created_at']

    def validate(self, data):
        project = data.get('project')
        assignee = data.get('assignee')

        if project and assignee:
            if not project.members.filter(id=assignee.id).exists():
                raise serializers.ValidationError({"assignee": "Исполнитель должен быть участником проекта."})
        return data


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True) # Чтобы во Flutter приходил ник отправителя

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'text', 'created_at']