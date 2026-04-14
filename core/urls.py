from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static
from api.views import RegisterView, ManageProfileView
from api.views import ChangePasswordView
from api.views import (
    SendFriendRequestView, IncomingRequestsView,
    RespondFriendRequestView, ListFriendsView
)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/users/me/', ManageProfileView.as_view(), name='manage_profile'),
    path('api/users/me/change-password/', ChangePasswordView.as_view(), name='change_password'),
    # Генерация схемы
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Сам интерфейс Swagger
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    path('api/users/friends/', ListFriendsView.as_view(), name='list_friends'),
    path('api/users/friends/request/<str:username>/', SendFriendRequestView.as_view(), name='send_request'),
    path('api/users/friends/requests/incoming/', IncomingRequestsView.as_view(), name='incoming_requests'),

    # action должен быть строкой: 'accept' или 'reject'
    path('api/users/friends/requests/<int:pk>/<str:action>/', RespondFriendRequestView.as_view(),
         name='respond_request'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)