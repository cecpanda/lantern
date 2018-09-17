from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .lot import Lot


UserModel = get_user_model()


class ID(models.Model):
    created = models.DateTimeField('添加时间', auto_now_add=True)

    class Meta:
        verbose_name = '流水号'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.id}'


def default_order_sn():
    now = timezone.localtime()
    return now.strftime('%y%m%d-%H%M%S-%f')


class Order(models.Model):
    STATUS_CHOICES = (
        ('0', '未知'),
        ('1', '（停机）待生产签核'),
        ('2', '（停机）待责任工程签核'),
        ('3', '（停机）拒签'),
        ('4', '（停机）完成'),
        ('5', '（复机）待QC签核'),
        ('6', '（复机）待生产签核'),
        ('7', '（复机）拒签'),
        ('8', '（部分复机）完成'),
        ('9', '（复机）完成')
    )
    # 重写了主键，名字最好还用 id， 因为 action 中使用到 target_id
    id = models.CharField('编号', max_length=20, primary_key=True, default=default_order_sn)
    status = models.CharField('状态', choices=STATUS_CHOICES, max_length=2, default='0')
    next = models.CharField('下一步', choices=STATUS_CHOICES, max_length=2, blank=True, null=True, default='0')

    user = models.ForeignKey(UserModel, related_name='startorders', on_delete=models.PROTECT, verbose_name='开单人员')
    # 开单工程不能为空，否则 element-ui 的表头过滤功能不保
    group = models.ForeignKey(Group, related_name='startorders', on_delete=models.PROTECT, verbose_name='开单工程')
    created = models.DateTimeField('开单时间', auto_now_add=True)

    mod_user = models.ForeignKey(UserModel, related_name='modstartorders', blank=True, null=True,
                                 on_delete=models.PROTECT, verbose_name='修改人员')
    modified = models.DateTimeField('修改时间', auto_now=True)

    found_step = models.CharField('发现站点', max_length=30)
    found_time = models.DateTimeField('发现时间')
    # charge_group = models.ForeignKey(Group, related_name='chargeorders', on_delete=models.PROTECT,
    #                                  blank=True, null=True, verbose_name='责任工程')
    charge_group = models.ForeignKey(Group, related_name='chargeorders', on_delete=models.PROTECT,
                                     verbose_name='责任工程')
    # 设备对应关系都不需要了，鬼鬼，垃圾系统
    # eq = models.ManyToManyField(Eq, related_name='startorders', verbose_name='停机设备')
    eq = models.CharField('停机设备', max_length=50)
    kind = models.CharField('停机机种', max_length=30)
    step = models.CharField('停机站点', max_length=50)

    reason = models.TextField('停机原因', max_length=100)
    # 做验证，必须停机设备的组下的人员
    # 7.20 需求改了，这两项作为字符串处理就行了
    # users = models.ManyToManyField(UserModel, related_name='noticed_users', verbose_name='通知生产人员')
    # charge_users = models.ManyToManyField(UserModel, related_name='noticed_charge_users', verbose_name='通知制程人员')
    users = models.CharField('通知生产人员', max_length=10)
    charge_users = models.CharField('通知制程人员', max_length=10)

    desc = models.TextField('异常描述', max_length=300)
    start_time = models.DateTimeField('受害开始时间', blank=True, null=True)
    end_time = models.DateTimeField('受害结束时间', blank=True, null=True)
    lot_num = models.CharField('受害批次数', max_length=10, blank=True, null=True)
    # lots = models.ManyToManyField(Lot, related_name="+", blank=True, verbose_name='异常批次/基板')
    lots = models.TextField('异常批次/基板', max_length=100, blank=True, null=True)

    condition = models.TextField('复机条件', max_length=200)
    defect_type = models.NullBooleanField('绝对不良', blank=True, null=True, default=None)

    class Meta:
        verbose_name = '停机单'
        verbose_name_plural = verbose_name
        ordering = ('-created', )

    # def get_absolute_url(self):
    #     return reverse('tft:start-detail', args=(self.id,))

    def __str__(self):
        return self.id


class Audit(models.Model):
    order = models.OneToOneField(Order, related_name='startaudit', on_delete=models.CASCADE, verbose_name='订单')
    p_signer = models.ForeignKey(UserModel, related_name='p_startaudit', blank=True, null=True,
                                 on_delete=models.PROTECT, verbose_name='生产领班签核')
    p_time = models.DateTimeField('生产签核时间', blank=True, null=True)
    recipe_close = models.CharField('Recipe关闭人员', blank=True, null=True, max_length=10)
    recipe_confirm = models.CharField('Recipe确认人员', blank=True, null=True, max_length=10)

    c_signer = models.ForeignKey(UserModel, related_name='c_startaudits', blank=True, null=True,
                                 on_delete=models.PROTECT, verbose_name='责任工程签核')
    c_time = models.DateTimeField('责任工程签核时间', blank=True, null=True)
    rejected = models.BooleanField('是否拒签', default=False)
    reason = models.TextField('拒签理由', max_length=100, blank=True, null=True)

    created = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '停机签核'
        verbose_name_plural = verbose_name
        ordering = ('-created',)

    def __str__(self):
        return self.order.id


class RecoverOrder(models.Model):
    order = models.ForeignKey(Order, related_name='recoverorders', on_delete=models.CASCADE, verbose_name='订单')
    user = models.ForeignKey(UserModel, related_name='recoverorders', on_delete=models.PROTECT, verbose_name='申请人')
    created = models.DateTimeField('申请时间', auto_now_add=True)

    mod_user = models.ForeignKey(UserModel, related_name='modrecoverorders', blank=True, null=True,
                                 on_delete=models.PROTECT, verbose_name='修改人员')
    modified = models.DateTimeField('修改时间', auto_now=True)

    solution = models.TextField('责任单位对策说明', max_length=200)
    explain = models.TextField('先行lot结果说明', max_length=200)

    partial = models.BooleanField('部分复机', default=False)
    # eq = models.ManyToManyField(Eq, related_name='+', verbose_name='部分复机设备')
    eq = models.CharField('部分复机设备', max_length=50, blank=True, null=True)
    kind = models.CharField('部分复机机种', max_length=30, blank=True, null=True)
    step = models.CharField('部分复机站点', max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = '复机单'
        verbose_name_plural = verbose_name
        ordering = ('-created',)

    def __str__(self):
        return f'{self.order.id} <{self.id}>'


class RecoverAudit(models.Model):
    recover_order = models.OneToOneField(RecoverOrder, related_name='audit', on_delete=models.CASCADE,
                                         verbose_name='复机单')

    qc_signer = models.ForeignKey(UserModel, related_name='qc_recoveraudits', blank=True, null=True,
                                  on_delete=models.PROTECT, verbose_name='工程品质签核')
    qc_time = models.DateTimeField('品质签核时间', blank=True, null=True)

    p_signer = models.ForeignKey(UserModel, related_name='p_recoveraudit', blank=True, null=True,
                                 on_delete=models.PROTECT, verbose_name='生产领班签核')
    p_time = models.DateTimeField('生产签核时间', blank=True, null=True)

    rejected = models.BooleanField('拒签', default=False)
    reason = models.TextField('拒签理由', max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = '复机签核'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.recover_order.order.id


def report_handler(instance, filename):
    # instance.id 还未存在
    # filename = os.path.split(filename.strip())[-1]
    # name, suffix = os.path.splitext(filename)
    return f"reports/{instance.order.id}/{filename}"


class Report(models.Model):
    order = models.ForeignKey(Order, related_name='reports', on_delete=models.CASCADE, verbose_name='订单')
    file = models.FileField(upload_to=report_handler, verbose_name='调查报告')

    class Meta:
        verbose_name = '调查报告'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.order.id


class Remark(models.Model):
    user = models.ForeignKey(UserModel, related_name='remarks', on_delete=models.PROTECT, verbose_name='用户')
    order = models.ForeignKey(Order, related_name='remarks', on_delete=models.CASCADE, verbose_name='订单')
    content = models.TextField('内容', max_length=500)

    created = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        ordering = ['-created']
        verbose_name = '生产批注'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.order.id
