from general.models import User

from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny

from general.api.serializers import UserRegistrationSerializer
from general.api.serializers import UserListSerializer


class UserViewSet(
    CreateModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    queryset = User.objects.all().order_by("-id")

    def get_serializer_class(self):
        if self.action == "create":
            return UserRegistrationSerializer
        return UserListSerializer

    def get_permissions(self): # Создать пользователя без аутентификации, получение всех только после аутентификации
        if self.action == "create":
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()