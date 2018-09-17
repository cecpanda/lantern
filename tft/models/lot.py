from django.db import models


class LotInfo(models.Model):
    kind = models.CharField('机种', max_length=4)
    size = models.CharField('大小', blank=True, null=True, max_length=10)
    height = models.CharField('高度', blank=True, null=True, max_length=10)

    class Meta:
        verbose_name = '机种信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.kind


class Lot(models.Model):
    # 不要 lotinfo 了，直接输入
    name = models.CharField('批次', blank=True, null=True, max_length=14)
    created = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '批次'
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
