from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

from rest_framework import serializers


UserModel = get_user_model()


class JwtResponseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('id', 'username')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class UserOfGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('username', 'realname', 'email',  'mobile',
                  'phone', 'avatar', 'gender')


class GroupUserSerializer(serializers.ModelSerializer):
    user_set = UserOfGroupSerializer(many=True)

    class Meta:
        model = Group
        fields = ('id', 'name', 'user_set')


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = UserModel
        fields = ('username', 'realname', 'email',  'mobile', 'phone',
                  'avatar', 'gender',  'groups', 'date_joined')
        read_only_fields = ('username',)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ('username', 'realname', 'email',  'mobile', 'phone',
                  'avatar', 'gender')
        read_only_fields = ('username',)


class PasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(style={'input_type': 'password'})


class FollowSerializer(serializers.Serializer):
    user_from = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_to = serializers.CharField(label='关注者', required=True)

    def validate_user_to(self, value):
        try:
            user_to = UserModel.objects.get(username=value)
        except:
            raise serializers.ValidationError('您要（取消）关注的用户不存在')

        if user_to == self.context['request'].user:
            raise serializers.ValidationError('您为什么要（取消）关注自己呢')

        return value


# 判断 follow status，用不到
class FollowStatusSerializer(serializers.Serializer):
    user_from = serializers.CharField(label='用户A', required=True)
    user_to = serializers.CharField(label='用户B', required=True)


# 在 Follow 中实现
class ListFollowSerializer(serializers.Serializer):
    following = UserOfGroupSerializer(many=True)
    followers = UserOfGroupSerializer(many=True)


# 在 User 中实现
class FollowingSerializer(serializers.ModelSerializer):
    following = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('following',)

    def get_following(self, obj):
        following = obj.following.all()
        return [user.username for user in following]


class FollowersSerializer(serializers.ModelSerializer):
    followers = serializers.SerializerMethodField()

    class Meta:
        model = UserModel
        fields = ('followers',)

    def get_followers(self, obj):
        followers = obj.followers.all()
        return [user.username for user in followers]
