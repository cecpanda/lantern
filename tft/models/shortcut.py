from django.db import models


class Shortcut(models.Model):
    name = models.CharField('标题', max_length=10)

    class Meta:
        verbose_name = '快捷标题'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ShortcutContent(models.Model):
    name = models.ForeignKey(Shortcut, related_name='contents', on_delete=models.CASCADE, verbose_name='标题')
    content = models.CharField('内容', max_length=50)

    class Meta:
        verbose_name = '快捷内容'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name.name


# class ReasonShortcut(models.Model):
#     name = models.ForeignKey(Shortcut, related_name='reasons', on_delete=models.CASCADE, verbose_name='标题')
#     content = models.TextField('内容', max_length=100)
#
#     def __str__(self):
#         return self.name.name

#
# class DescShortCut(models.Model):
#     name = models.ForeignKey(Shortcut, related_name='descs', on_delete=models.CASCADE, verbose_name='标题')
#     content = models.TextField('内容', max_length=300)
#
#     def __str__(self):
#         return self.name.name
