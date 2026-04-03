import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from api.models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Получаем ID комнаты из URL
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope.get('user')

        # Если юзер не авторизован (токен неверный или не передан)
        if not self.user or self.user.is_anonymous:
            await self.close()
            return

        # Проверяем права доступа к этому чату
        has_access = await self.check_room_access(self.room_id, self.user)
        if not has_access:
            await self.close()
            return

        # Подключаем к группе Redis
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Отключаем от группы
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')

        if message:
            # Сохраняем сообщение в базу
            await self.save_message(self.room_id, self.user, message)

            # Рассылаем всем участникам комнаты
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': self.user.username
                }
            )

    async def chat_message(self, event):
        # Отправляем JSON обратно клиенту
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender']
        }))

    # Вспомогательные синхронные методы для работы с БД (оборачиваем в async)
    @database_sync_to_async
    def save_message(self, room_id, user, text):
        room = ChatRoom.objects.get(id=room_id)
        Message.objects.create(room=room, sender=user, text=text)

    @database_sync_to_async
    def check_room_access(self, room_id, user):
        try:
            room = ChatRoom.objects.get(id=room_id)
            if room.type == 'PROJECT':
                return user.is_superuser or user in room.project.members.all()
            return user in room.participants.all()
        except ChatRoom.DoesNotExist:
            return False