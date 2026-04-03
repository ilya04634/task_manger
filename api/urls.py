from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# Обязательно добавь новые Views в импорт!
from .views import ProjectViewSet, TaskViewSet, AddFriendView, MessageHistoryView, UserSearchView, \
    RegisterDeviceTokenView

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
path('users/device-token/', RegisterDeviceTokenView.as_view(), name='device-token'),
    path('', include(router.urls)),

    # Поиск пользователей: /api/users/search/?q=никнейм
    path('users/search/', UserSearchView.as_view(), name='user-search'),

    # Добавление в друзья: /api/users/friends/add/никнейм/
    path('users/friends/add/<str:username>/', AddFriendView.as_view(), name='add-friend'),

    # История чата: /api/chat/1/messages/
    path('chat/<int:room_id>/messages/', MessageHistoryView.as_view(), name='chat-history'),
]