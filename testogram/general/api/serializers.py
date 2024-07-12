from rest_framework import serializers
from django.db.models import Q
from general.models import (
    User,
    Post,
    Comment,
    Reaction,
    Chat,
    Message,
)


# Регистрация
class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "password",
            "email",
            "first_name",
            "last_name",
        )

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()

        return user


# Получаем всех пользователей
class UserListSerializer(serializers.ModelSerializer):
    is_friend = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "is_friend")

    def get_is_friend(self, obj) -> bool:
        current_user = self.context["request"].user
        return current_user in obj.friends.all()


# Посты конкретного пользователя
class NestedPostListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "body",
            "created_at",
        )


# Получаем информацию о пользователе
class UserRetrieveSerializer(serializers.ModelSerializer):
    is_friend = serializers.SerializerMethodField()
    friend_count = serializers.SerializerMethodField()
    posts = NestedPostListSerializer(many=True)

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "is_friend",
            "friend_count",
            "posts",
        )

    def get_friend_count(self, obj) -> int:
        return obj.friends.count()

    def get_is_friend(self, obj) -> bool:
        return obj in self.context["request"].user.friends.all()


# Создание и обновление поста
class PostCreateUpdateSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "body",
        )

# Получаем автора поста
class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name")

# Полуаем данные поста с сокращенным текстом
class PostListSerializer(serializers.ModelSerializer):
    author = UserShortSerializer()
    body = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "body",
            "created_at",
        )

    def get_body(self, obj) -> str:
        if len(obj.body) > 128:
            return obj.body[:125] + "..."
        return obj.body

# Получаем пост полностью по id
class PostRetrieveSerializer(serializers.ModelSerializer):
    author = UserShortSerializer()
    my_reaction = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "body",
            "my_reaction",
            "created_at",
        )

    def get_my_reaction(self, obj) -> str:
        reaction = self.context["request"].user.reactions.filter(post=obj).last()
        return reaction.value if reaction else ""


# Добавить комментарий к посту
class CommentSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    def get_fields(self):
        fields = super().get_fields()
        if self.context["request"].method == "GET":
            fields["author"] = UserShortSerializer(read_only=True)
        return fields

    class Meta:
        model = Comment
        fields = (
            "id",
            "author",
            "post",
            "body",
            "created_at",
        )

# Реакции
class ReactionSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    class Meta:
        model = Reaction
        fields = (
            "id",
            "author",
            "post",
            "value",
        )

    def create(self, validated_data):
        reaction = Reaction.objects.filter(
            post=validated_data["post"],
            author=validated_data["author"],
        ).last()

        if not reaction:
            return Reaction.objects.create(**validated_data)

        if reaction.value == validated_data["value"]:
            reaction.value = None
        else:
            reaction.value = validated_data["value"]
        reaction.save()

        return reaction


# Личные чаты
class ChatSerializer(serializers.ModelSerializer):
    user_1 = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    class Meta:
        model = Chat
        fields = ("id", "user_1", "user_2")

    def create(self, validated_data):
        request_user = validated_data["user_1"]
        second_user = validated_data["user_2"]

        chat = Chat.objects.filter(
            Q(user_1=request_user, user_2=second_user)
            | Q(user_1=second_user, user_2=request_user)
        ).first()
        if not chat:
            chat = Chat.objects.create(
                user_1=request_user,
                user_2=second_user,
            )

        return chat

    def to_representation(self, obj):
        representation = super().to_representation(obj)
        representation["user_2"] = (
            obj.user_1.pk
            if obj.user_2 == self.context["request"].user
            else obj.user_2.pk
        )
        return representation

class ChatListSerializer(serializers.ModelSerializer):
    companion_name = serializers.SerializerMethodField()
    last_message_content = serializers.SerializerMethodField()
    last_message_datetime = serializers.DateTimeField()

    class Meta:
        model = Chat
        fields = (
            "id",
            "companion_name",
            "last_message_content",
            "last_message_datetime",
        )

    def get_last_message_content(self, obj) -> str:
        return obj.last_message_content

    def get_companion_name(self, obj) -> str:
        companion = obj.user_1 if obj.user_2 == self.context["request"].user else obj.user_2
        return f"{companion.first_name} {companion.last_name}"


# Получаем все сообщения
class MessageListSerializer(serializers.ModelSerializer):
    message_author = serializers.CharField()

    class Meta:
        model = Message
        fields = ("id", "content", "message_author", "created_at")


# Отправка сообщения и удаление
class MessageSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )

    def validate(self, attrs):
        chat = attrs["chat"]
        author = attrs["author"]
        if chat.user_1 != author and chat.user_2 != author:
            raise serializers.ValidationError("Вы не являетесь участником этого чата.")
        return super().validate(attrs)

    class Meta:
        model = Message
        fields = ("id", "author", "content", "chat", "created_at")