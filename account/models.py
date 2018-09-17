from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, Group
# from rest_framework.reverse import reverse


class User(AbstractUser):
    GENDER_CHOICES = (
        ("M", "男"),
        ("F", "女")
    )
    # username
    realname = models.CharField('真名', max_length=10, blank=True, null=True)
    email = models.EmailField('邮箱', max_length=100, blank=True, null=True)
    mobile = models.CharField("手机", max_length=11, blank=True, null=True)
    phone = models.CharField('电话', max_length=6, blank=True, null=True)
    avatar = models.ImageField('头像', upload_to='avatars/%Y/%m', blank=True,
                               null=True, default="avatars/default.png")
    gender = models.CharField("性别", max_length=1, choices=GENDER_CHOICES,
                              default="M")
    following = models.ManyToManyField('self', through='Follow', related_name='followers', symmetrical=False)

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_absolute_url(self):
        return reverse('account:user-detail', args=[self.username])

    def __str__(self):
        return self.username


class Follow(models.Model):
    user_from = models.ForeignKey(User, related_name='rel_from', on_delete=models.CASCADE, verbose_name='用户')
    user_to = models.ForeignKey(User, related_name='rel_to', on_delete=models.CASCADE, verbose_name='关注')
    created = models.DateTimeField('关注时间', auto_now_add=True)

    class Meta:
        ordering = ('-created',)
        verbose_name = '关注'
        verbose_name_plural = verbose_name
        unique_together = ('user_from', 'user_to')

    def __str__(self):
        return f'{self.user_from.username} 关注 {self.user_to.username}'


class GroupSetting(models.Model):
    group = models.OneToOneField(Group, related_name='settings', on_delete=models.CASCADE, verbose_name='科室')
    code = models.CharField('代码', max_length=5, unique=True)

    class Meta:
        verbose_name = '科室代码'
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.group.name

# Group.add_to_class('department', models.ForeignKey('self',
#                                                    related_name='groups',
#                                                    blank=True,
#                                                    null=True,
#                                                    on_delete=models.PROTECT,
#                                                    verbose_name='部门'))
