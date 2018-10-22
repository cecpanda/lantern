from django.db import models
from django.contrib.auth.models import Group


class Mark(models.Model):
    group = models.OneToOneField(Group, related_name='mark', on_delete=models.CASCADE, verbose_name='科室')
    mark = models.IntegerField(verbose_name='标记值')

    class Meta:
        verbose_name = '标记值'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.group.name
