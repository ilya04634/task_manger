from rest_framework import viewsets, status, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import models
from .models import Project, Task, User, ChatRoom, TaskAttachment
from .serializers import ProjectSerializer, TaskSerializer
from .permissions import IsSuperUserOrProjectMember, IsProjectAdminOrReadOnly
from rest_framework.decorators import action
from rest_framework import generics
from .models import Message # Убедись, что импортировал Message
from .serializers import MessageSerializer, UserSerializer
from rest_framework.views import APIView
from .models import FCMDeviceToken
from rest_framework.parsers import MultiPartParser, FormParser
from .services import send_push_notification
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, inline_serializer
from rest_framework import serializers


@extend_schema_view(
    list=extend_schema(summary="Список проектов", description="Возвращает список проектов пользователя. Суперюзер видит все."),
    retrieve=extend_schema(summary="Детали проекта", description="Получить информацию об одном проекте по ID."),
    create=extend_schema(summary="Создать проект", description="Создатель автоматически становится админом. Можно передать массив member_ids."),
    update=extend_schema(summary="Обновить проект", description="Полное обновление (только для админа проекта)."),
    partial_update=extend_schema(summary="Частичное обновление", description="Частичное обновление полей."),
    destroy=extend_schema(summary="Удалить проект", description="Удаление проекта (только для админа).")
)
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrProjectMember, IsProjectAdminOrReadOnly]


    def get_queryset(self):
        user = self.request.user
        # Модератор и root видят все проекты
        if user.role == 'MODERATOR' or user.is_superuser:
            return Project.objects.all().order_by('-id')
        # Обычные юзеры (и админы проектов) видят только те проекты, где они состоят
        return Project.objects.filter(members=user).order_by('-id')

    def perform_create(self, serializer):
        # Создаем проект
        project = serializer.save()

        # Кто создал - тот и админ (плюс добавляем его в участники)
        project.admins.add(self.request.user)
        project.members.add(self.request.user)

        # Если модератор при создании сразу передал member_ids или admin_ids,
        # сериализатор сохранит их автоматически, мы лишь добавляем создателя для надежности

        ChatRoom.objects.create(type='PROJECT', project=project)

    @extend_schema(
        summary="Назначить админа проекта",
        description="Добавляет участника проекта в список админов. Доступно Модераторам и текущим Админам проекта.",
        request=inline_serializer(
            name='AddAdmin',
            fields={'user_id': serializers.IntegerField()}
        ),
        responses={200: OpenApiResponse(description="Пользователь назначен админом")}
    )
    @action(detail=True, methods=['post'])
    def add_admin(self, request, pk=None):
        project = self.get_object()
        user_id = request.data.get('user_id')
        user_to_promote = get_object_or_404(User, id=user_id)

        if user_to_promote not in project.members.all():
            return Response({"error": "Пользователь должен быть участником проекта"},
                            status=status.HTTP_400_BAD_REQUEST)

        project.admins.add(user_to_promote)
        return Response({"status": f"{user_to_promote.username} теперь админ проекта {project.name}"})

    @extend_schema(
        summary="Разжаловать админа проекта",
        description="Удаляет пользователя из списка админов проекта (он остается обычным участником).",
        request=inline_serializer(
            name='RemoveAdmin',
            fields={'user_id': serializers.IntegerField()}
        ),
        responses={200: OpenApiResponse(description="Пользователь больше не админ")}
    )
    @action(detail=True, methods=['post'])
    def remove_admin(self, request, pk=None):
        project = self.get_object()
        user_id = request.data.get('user_id')
        user_to_demote = get_object_or_404(User, id=user_id)

        if user_to_demote in project.admins.all():
            # Защита: нельзя разжаловать последнего админа или самого себя (опционально)
            project.admins.remove(user_to_demote)
            return Response({"status": f"{user_to_demote.username} больше не админ проекта"})

        return Response({"error": "Пользователь не является админом"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(summary="Список задач", description="Возвращает личные задачи и задачи из проектов пользователя."),
    retrieve=extend_schema(summary="Детали задачи", description="Получить одну задачу по ID."),
    create=extend_schema(summary="Создать задачу", description="Если project=null, задача личная. Если передан assignee, он должен быть участником проекта."),
    update=extend_schema(summary="Обновить задачу", description="Доступно только создателю (для личных) или админу (для проектных)."),
    partial_update=extend_schema(summary="Частично обновить задачу", description="Частичное изменение полей."),
    destroy=extend_schema(summary="Удалить задачу", description="Удаление задачи.")
)
class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsSuperUserOrProjectMember, IsProjectAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        # Модератор и root видят все задачи
        if user.role == 'MODERATOR' or user.is_superuser:
            return Task.objects.all().order_by('-created_at')

        # Остальные видят свои личные и задачи своих проектов
        return Task.objects.filter(
            models.Q(creator=user, project__isnull=True) |
            models.Q(project__members=user)
        ).distinct().order_by('-created_at')

    def perform_create(self, serializer):
        task = serializer.save(creator=self.request.user)
        if task.assignee and task.assignee != self.request.user:
            # Отправляем push-уведомление
            send_push_notification(
                user=task.assignee,
                title="Новая задача!",
                body=f"Вам назначена задача: {task.title}",
                data={"task_id": str(task.id), "type": "new_task"}
            )

    @extend_schema(
        summary="Изменить статус задачи",
        description="Быстрое изменение статуса задачи без передачи остальных полей.",
        request=inline_serializer(
            name='StatusChange',
            fields={'status': serializers.ChoiceField(choices=Task.STATUS_CHOICES)}
        ),
        responses={200: OpenApiResponse(description="Статус успешно обновлен")}
    )

    @action(detail=True, methods=['patch'])
    def change_status(self, request, pk=None):
        task = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Task.STATUS_CHOICES).keys():
            return Response({"error": "Неверный статус"}, status=status.HTTP_400_BAD_REQUEST)

        task.status = new_status
        task.save()
        return Response({'status': 'Статус обновлен на ' + new_status})

    @extend_schema(
        summary="Загрузить файл к задаче",
        description="Загрузка вложения (картинки, документа). Использовать формат multipart/form-data.",
        request={
            'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
        responses={200: OpenApiResponse(description="Файл успешно загружен")}
    )

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_file(self, request, pk=None):
        task = self.get_object()
        file_obj = request.FILES.get('file')

        if not file_obj:
            return Response({"error": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST)

        attachment = TaskAttachment.objects.create(task=task, file=file_obj)
        return Response({
            "status": "Файл загружен",
            "file_url": request.build_absolute_uri(attachment.file.url)
        })

class AddFriendView(views.APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Добавить в друзья",
        description="Добавляет пользователя в друзья по его username. Автоматически создает личную комнату чата.",
        responses={
            200: OpenApiResponse(description="Успех: Друг добавлен"),
            400: OpenApiResponse(description="Ошибка: Нельзя добавить себя"),
            404: OpenApiResponse(description="Ошибка: Пользователь не найден")
        }
    )
    def post(self, request, username):
        friend = get_object_or_404(User, username=username)
        if friend != request.user:
            request.user.friends.add(friend)
            room, created = ChatRoom.objects.get_or_create(type='PERSONAL')
            if created:
                room.participants.add(request.user, friend)
            return Response({"detail": "Друг добавлен"}, status=status.HTTP_200_OK)
        return Response({"detail": "Нельзя добавить себя"}, status=status.HTTP_400_BAD_REQUEST)


# View для получения истории сообщений конкретной комнаты
class MessageHistoryView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="История сообщений чата",
        description="Получить пагинированный список старых сообщений комнаты перед подключением к WebSocket.",
        responses={200: MessageSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        room_id = self.kwargs['room_id']
        room = get_object_or_404(ChatRoom, id=room_id)

        # Проверяем, имеет ли пользователь право читать этот чат
        user = self.request.user
        if room.type == 'PROJECT':
            if not (user.is_superuser or user in room.project.members.all()):
                return Message.objects.none()
        elif user not in room.participants.all():
            return Message.objects.none()

        # Возвращаем сообщения, отсортированные по времени (старые первыми)
        return Message.objects.filter(room=room).order_by('-created_at') # Новые сверху для удобной пагинации во Flutter


# View для поиска пользователей по нику (username)
class UserSearchView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Изменить глобальную роль пользователя",
        description="Только для Модераторов. Позволяет изменить роль юзера на MODERATOR или USER.",
        request=inline_serializer(
            name='GlobalRoleChange',
            fields={'role': serializers.ChoiceField(choices=User.ROLE_CHOICES)}
        ),
        responses={200: OpenApiResponse(description="Роль изменена")}
    )
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsProjectAdminOrReadOnly])
    def set_global_role(self, request, pk=None):
        # IsProjectAdminOrReadOnly уже разрешает это только модераторам/root
        user_to_change = get_object_or_404(User, id=pk)
        new_role = request.data.get('role')

        if new_role not in dict(User.ROLE_CHOICES).keys():
            return Response({"error": "Неверная роль"}, status=status.HTTP_400_BAD_REQUEST)

        user_to_change.role = new_role
        user_to_change.save()
        return Response({"status": f"Глобальная роль пользователя {user_to_change.username} изменена на {new_role}"})

    @extend_schema(
        summary="Поиск пользователей",
        description="Ищет пользователей по совпадению никнейма (без учета регистра).",
        parameters=[
            OpenApiParameter(name='q', description='Текст для поиска (никнейм)', required=True, type=str)
        ],
        responses={200: UserSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if query:
            return User.objects.filter(username__icontains=query).exclude(id=self.request.user.id).order_by('username')
        return User.objects.none()

class RegisterDeviceTokenView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Регистрация FCM токена",
        description="Отправьте сюда FCM-токен устройства (при входе во Flutter приложение), чтобы сервер мог слать Push-уведомления.",
        request=inline_serializer(
            name='FCMTokenInput',
            fields={'token': serializers.CharField(help_text="FCM Токен от Firebase")}
        ),
        responses={200: OpenApiResponse(description="Токен успешно сохранен")}
    )
    def post(self, request):
        token = request.data.get('token')
        if token:
            FCMDeviceToken.objects.get_or_create(user=request.user, token=token)
            return Response({"status": "Токен сохранен"})
        return Response({"error": "Токен не передан"}, status=status.HTTP_400_BAD_REQUEST)