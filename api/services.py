import firebase_admin
from firebase_admin import messaging
from .models import FCMDeviceToken


def send_push_notification(user, title, body, data=None):
    """
    Функция для отправки push-уведомления конкретному пользователю.
    """
    # Защита: если Firebase не настроен (нет ключа), просто выходим
    if not firebase_admin._apps:
        print(f"[{user.username}] Пуш пропущен: Firebase не инициализирован.")
        return

    tokens = FCMDeviceToken.objects.filter(user=user).values_list('token', flat=True)

    if not tokens:
        return

    # Формируем сообщение
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},  # Сюда можно передать скрытые данные (например, ID чата для перехода)
        tokens=list(tokens),
    )

    try:
        # Отправляем сообщение через сервера Google
        response = messaging.send_multicast(message)

        # Если есть невалидные токены (например, юзер удалил приложение), их стоит удалить из БД
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # Ошибки 'messaging/invalid-registration-token' или 'messaging/registration-token-not-registered'
                    failed_tokens.append(tokens[idx])

            if failed_tokens:
                FCMDeviceToken.objects.filter(token__in=failed_tokens).delete()

    except Exception as e:
        print(f"Ошибка отправки Push: {e}")