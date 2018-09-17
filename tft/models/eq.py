from django.db import models
from django.contrib.auth.models import Group


class EqKind(models.Model):
    name = models.CharField('装置类别', max_length=4)
    group = models.ForeignKey(Group, related_name='eqkinds',
                              on_delete=models.PROTECT, verbose_name='科室')

    class Meta:
        verbose_name = '装置类别'
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Eq(models.Model):
    kind = models.ForeignKey(EqKind, related_name='eqs',
                             on_delete=models.PROTECT, verbose_name='装置类别')
    name = models.CharField('装置名', max_length=8)

    class Meta:
        verbose_name = '装置'
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
