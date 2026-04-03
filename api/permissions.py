from rest_framework import permissions


class IsSuperUserOrProjectMember(permissions.BasePermission):
    """
    Разрешает доступ 모дераторам (и root).
    Для проектов и задач проверяет, является ли юзер участником.
    """

    def has_object_permission(self, request, view, obj):
        # Модератор (и root) видит всё
        if request.user.role == 'MODERATOR' or request.user.is_superuser:
            return True

        # Для проекта
        if hasattr(obj, 'members'):
            return request.user in obj.members.all()

        # Для задачи
        if hasattr(obj, 'project'):
            if obj.project is None:
                return obj.creator == request.user
            return request.user in obj.project.members.all()

        return False


class IsProjectAdminOrReadOnly(permissions.BasePermission):
    """
    Изменять проекты и задачи (создавать, удалять, редактировать)
    может только Модератор или Админ конкретного проекта.
    """

    def has_object_permission(self, request, view, obj):
        # Читать (GET запросы) могут все, кто прошел предыдущий пермишен
        if request.method in permissions.SAFE_METHODS:
            return True

        # Модератор (и root) может всё
        if request.user.role == 'MODERATOR' or request.user.is_superuser:
            return True

        # Для проекта: проверям, является ли юзер одним из админов
        if hasattr(obj, 'admins'):
            return request.user in obj.admins.all()

        # Для задачи: создатель личной задачи может ее менять
        if hasattr(obj, 'project'):
            if obj.project is None:
                return obj.creator == request.user
            # Если задача в проекте, менять ее может только админ проекта
            return request.user in obj.project.admins.all()

        return False