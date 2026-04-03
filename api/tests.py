from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Project, Task, ChatRoom

User = get_user_model()


class TaskManagerAPITests(APITestCase):

    def setUp(self):
        """
        Этот метод запускается ПЕРЕД каждым тестом.
        Здесь мы готовим "чистую" базу данных: создаем юзеров.
        """
        self.user1 = User.objects.create_user(username='user1', password='testpassword123')
        self.user2 = User.objects.create_user(username='user2', password='testpassword123')
        self.superuser = User.objects.create_superuser(username='admin', password='adminpassword')

    # --- 1. ТЕСТЫ АВТОРИЗАЦИИ ---

    def test_get_jwt_token(self):
        """Проверка получения токена по логину и паролю"""
        url = reverse('token_obtain_pair')
        data = {'username': 'user1', 'password': 'testpassword123'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    # --- 2. ТЕСТЫ ПРОЕКТОВ И ПРАВ ДОСТУПА ---

    def test_create_project(self):
        """Проверка создания проекта"""
        # Авторизуем пользователя (DRF сделает это без токена для тестов)
        self.client.force_authenticate(user=self.user1)
        url = reverse('project-list')
        data = {'name': 'Новый проект', 'description': 'Описание'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 1)
        project = Project.objects.get()
        self.assertEqual(project.admin, self.user1)
        self.assertIn(self.user1, project.members.all())
        # Проверяем, что автоматически создалась комната для чата
        self.assertEqual(ChatRoom.objects.filter(type='PROJECT', project=project).count(), 1)

    def test_project_isolation(self):
        """Проверка, что user2 не видит проект user1"""
        # user1 создает проект
        project = Project.objects.create(name='Секретный проект', admin=self.user1)
        project.members.add(self.user1)

        # Авторизуемся как user2 и пытаемся получить список проектов
        self.client.force_authenticate(user=self.user2)
        url = reverse('project-list')
        response = self.client.get(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # В ответе должен быть пустой массив, так как user2 не участник
        self.assertEqual(response.data['count'], 0)

    # --- 3. ТЕСТЫ ЗАДАЧ ---

    def test_create_personal_task(self):
        """Проверка создания личной задачи (без проекта)"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('task-list')
        data = {'title': 'Купить молоко', 'importance': 'HIGH'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.get().creator, self.user1)

    def test_change_task_status(self):
        """Проверка кастомного экшена change_status"""
        # Создаем задачу напрямую в БД
        task = Task.objects.create(title='Сделать верстку', creator=self.user1, status='TODO')

        self.client.force_authenticate(user=self.user1)
        # reverse для @action генерируется как 'имябазы-имяэкшена'
        url = reverse('task-change-status', args=[task.id])
        data = {'status': 'DONE'}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Обновляем объект из БД и проверяем статус
        task.refresh_from_db()
        self.assertEqual(task.status, 'DONE')

    def test_change_task_invalid_status(self):
        """Проверка защиты от неверных статусов"""
        task = Task.objects.create(title='Баг', creator=self.user1, status='TODO')
        self.client.force_authenticate(user=self.user1)
        url = reverse('task-change-status', args=[task.id])
        response = self.client.patch(url, {'status': 'HACKED'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- 4. ТЕСТЫ ДРУЗЕЙ И ЧАТА ---

    def test_add_friend_creates_chat(self):
        """Проверка добавления в друзья и создания личной комнаты чата"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('add-friend', args=[self.user2.username])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Проверяем, что user2 появился в друзьях у user1
        self.assertTrue(self.user1.friends.filter(id=self.user2.id).exists())

        # Проверяем, что создалась личная комната чата
        room = ChatRoom.objects.filter(type='PERSONAL').first()
        self.assertIsNotNone(room)
        # Оба пользователя должны быть участниками чата
        participants = room.participants.all()
        self.assertIn(self.user1, participants)
        self.assertIn(self.user2, participants)

    def test_search_users(self):
        """Проверка поиска пользователей"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('user-search')
        # Ищем user2
        response = self.client.get(url, {'q': 'user2'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # В результатах должен быть 1 юзер (user2), но не user1
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['username'], 'user2')