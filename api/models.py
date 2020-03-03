# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

import sys
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)


# 课程表
class Course(models.Model):
    """
    专题课程
    """
    name = models.CharField(max_length=128, unique=True, verbose_name="模块")
    course_img = models.CharField(max_length=255)
    course_type_choices = ((0, '付费'), (1, 'VIP专享'), (2, '学位课程'))
    course_type = models.SmallIntegerField(choices=course_type_choices)
    brief = models.TextField(verbose_name="课程概述",max_length=2048)
    level_choices = ((0, '初级'), (1, '中级'), (2, '高级'))
    level = models.SmallIntegerField(choices=level_choices, default=1)
    pub_date = models.DateField(verbose_name="发布日期", blank=True, null=True)
    period = models.PositiveIntegerField(verbose_name="建议学习周期(days)", default=7)
    order = models.IntegerField("课程顺序", help_text="从上一个课程数字往后排")
    attachment_path = models.CharField(max_length=128, verbose_name="课件路径", blank=True, null=True)
    status_choices = ((0, '上线'), (1, '下线'), (2, '预上线'))
    status = models.SmallIntegerField(choices=status_choices, default=0)

    order_details = GenericRelation('OrderDetail', related_query_name='course')
    coupon = GenericRelation('Coupon')
    price_policy = GenericRelation('PricePolicy')  # 用于GenericForeignKey反向查询，不会生成表字段

    def __str__(self):
        return '%s(%s)' % (self.name, self.get_course_type_display())


class CourseDetail(models.Model):
    """课程详情页内容"""
    course = models.OneToOneField('Course', on_delete=models.CASCADE)
    hours = models.IntegerField("课时")
    course_slogan = models.CharField(max_length=125, blank=True, null=True)
    video_brief_link = models.CharField(max_length=255, blank=True, null=True)
    why_study = models.TextField(verbose_name="为什么学习这门课程")
    what_to_study_brief = models.TextField(verbose_name="我将学到哪些内容")
    career_improvement = models.TextField(verbose_name="此项目如何有助于我的职业生涯")
    prerequisite = models.TextField(verbose_name="课程先修要求", max_length=1024)
    recommend_courses = models.ManyToManyField('Course', related_name='recommend_by', blank=True)
    teachers = models.ManyToManyField('Teacher', verbose_name="课程讲师")

    def __str__(self):
        return '%s' % self.course


class Teacher(models.Model):
    """讲师、导师表"""
    name = models.CharField(max_length=32)
    role_choices = ((0, '讲师'), (1, '导师'))
    role = models.SmallIntegerField(choices=role_choices,default=0)
    title = models.CharField(max_length=64, verbose_name="职位、职称")
    signature = models.CharField(max_length=255, help_text="导师签名", blank=True, null=True)
    image = models.CharField(max_length=128)
    brief = models.TextField(max_length=1024)

    def __str__(self):
        return self.name


class PricePolicy(models.Model):
    """价格与课程有效期表"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # 关联course or degree_course
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    valid_period_choices = ((1, '1天'), (3, '3天'),
                            (7, '1周'), (14, '2周'),
                            (30, '1个月'),
                            (60, '2个月'),
                            (90, '3个月'),
                            (120, '4个月'),
                            (180, '6个月'), (210, '12个月'),
                            (540, '18个月'), (720, '24个月'),
                            (722, '24个月'), (723, '24个月'),
                            )
    valid_period = models.SmallIntegerField(choices=valid_period_choices)
    price = models.FloatField()

    class Meta:
        unique_together = ('content_type', 'object_id', 'valid_period')

    def __str__(self):
        return "%s(%s)%s" %(self.content_object, self.get_valid_period_display(), self.price)


class CourseChapter(models.Model):
    """课程章节"""
    course = models.ForeignKey('Course', related_name='coursechapters', on_delete=models.CASCADE)
    chapter = models.SmallIntegerField(verbose_name="第几章", default=1)
    name = models.CharField(max_length=128)
    summary = models.TextField(verbose_name="章节介绍", blank=True, null=True)
    is_create = models.BooleanField(verbose_name="是否创建题库进度", default=True)
    pub_date = models.DateTimeField(verbose_name="发布日期", auto_now_add=True)

    class Meta:
        unique_together = ('course', 'chapter')

    def __str__(self):
        return "%s:(第%s章)%s" % (self.course, self.chapter, self.name)


class CourseSection(models.Model):
    """课时目录"""
    chapter = models.ForeignKey('CourseChapter', related_name='coursesection',on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    order = models.PositiveSmallIntegerField(verbose_name="课时排序", help_text="建议每个课时之间空1至2个值，以备后续插入课时")
    section_type_choice = ((0, '文档'), (1, '练习'), (2, '视频'))
    section_type = models.SmallIntegerField(choices=section_type_choice,default=2)
    section_link = models.CharField(max_length=255, blank=True, null=True, help_text="若是video，填vid,若是文档，填link")
    video_time = models.CharField(verbose_name="视频时长", blank=True, null=True, max_length=32)  # 仅在前端展示使用
    pub_date = models.DateTimeField(verbose_name="发布时间", auto_now_add=True)
    free_trail = models.BooleanField("是否可试看", default=False)
    is_flash = models.BooleanField(verbose_name="是否使用FLASH播放", default=False)
    player_choices = ((0, "CC"), (1, "POLYV"), (2, "ALI"))
    player = models.SmallIntegerField(choices=player_choices, default=1, help_text="视频播放器选择")

    def course_chapter(self):
        return self.chapter.chapter

    def course_name(self):
        return self.chapter.course.name

    class Meta:
        unique_together = ('chapter', 'section_link')

    def __str__(self):
        return "%s-%s" % (self.chapter, self.name)


class OftenAskedQuestion(models.Model):
    """常见问题"""
    content_type = models.ForeignKey(ContentType, limit_choices_to={'model__contains': 'course'},
                                     on_delete=models.CASCADE)  # 关联course or degree_course
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    question = models.CharField(max_length=255)
    answer = models.TextField(max_length=1024)

    def __str__(self):
        return "%s-%s" % (self.content_object, self.question)

    class Meta:
        unique_together = ('content_type', 'object_id', 'question')
        verbose_name_plural = "常见问题"


######################################## 优惠券 ########################################

class Coupon(models.Model):
    """优惠券生成规则"""
    name = models.CharField(max_length=64, verbose_name="活动名称")
    brief = models.TextField(blank=True, null=True, verbose_name="优惠券介绍")
    coupon_type_choices = ((0, '立减券'), (1, '满减券'), (2, '折扣券'))
    coupon_type = models.SmallIntegerField(choices=coupon_type_choices, default=0, verbose_name="券类型")
    money_equivalent_value = models.FloatField(verbose_name="等值货币",null=True,blank=True)
    off_percent = models.PositiveSmallIntegerField("折扣百分比", help_text="只针对折扣券，例7.9折，写79", blank=True, null=True)
    minimum_consume = models.PositiveIntegerField("最低消费", default=0, help_text="仅在满减券时填写此字段")
    content_type = models.ForeignKey(ContentType, blank=True, null=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField("绑定课程", blank=True, null=True, help_text="可以把优惠券跟课程绑定")
    content_object = GenericForeignKey('content_type', 'object_id')
    quantity = models.PositiveIntegerField("数量(张)", default=1)
    open_date = models.DateField("优惠券领取开始时间")
    close_date = models.DateField("优惠券领取结束时间")
    valid_begin_date = models.DateField(verbose_name="有效期开始时间", blank=True, null=True)
    valid_end_date = models.DateField(verbose_name="有效结束时间", blank=True, null=True)
    coupon_valid_days = models.PositiveIntegerField(verbose_name="优惠券有效期（天）", blank=True, null=True,
                                                    help_text="自券被领时开始算起")
    status_choices = ((0, "上线"), (1, "下线"))
    status = models.SmallIntegerField(choices=status_choices, default=0)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s(%s)" % (self.get_coupon_type_display(), self.name)


class CouponRecord(models.Model):
    """优惠券发放、消费纪录"""
    coupon = models.ForeignKey("Coupon", on_delete=models.CASCADE)
    account = models.ForeignKey("UserInfo", blank=True, null=True, verbose_name="使用者", on_delete=models.CASCADE)
    status_choices = ((0, '未使用'), (1, '已使用'), (2, '已过期'), (3, '未领取'))
    status = models.SmallIntegerField(choices=status_choices, default=0)
    get_time = models.DateTimeField(blank=True, null=True, verbose_name="领取时间", help_text="用户领取时间")
    used_time = models.DateTimeField(blank=True, null=True, verbose_name="使用时间")
    order = models.ForeignKey("Order", blank=True, null=True, verbose_name="关联订单",
                              on_delete=models.CASCADE)  # 一个订单可以有多个优惠券
    date = models.DateTimeField(auto_now_add=True, verbose_name="生成时间")

    # _coupon = GenericRelation("Coupon")

    def __str__(self):
        return self.coupon.name + "优惠券记录"


######################################## 订单表 ########################################

class Order(models.Model):
    """订单"""
    payment_type_choices = ((0, '微信'), (1, '支付宝'), (2, '优惠码'), (3, '贝里'), (4, '银联'))
    payment_type = models.SmallIntegerField(choices=payment_type_choices)
    payment_number = models.CharField(max_length=128, verbose_name="支付第3方订单号", null=True, blank=True)
    order_number = models.CharField(max_length=128, verbose_name="订单号", unique=True)  # 考虑到订单合并支付的问题
    account = models.ForeignKey("UserInfo", on_delete=models.CASCADE)
    actual_amount = models.FloatField(verbose_name="实付金额")
    # coupon = models.OneToOneField("Coupon", blank=True, null=True, verbose_name="优惠码") #一个订单可以有多个优惠券
    status_choices = ((0, '交易成功'), (1, '待支付'), (2, '退费申请中'), (3, '已退费'), (4, '主动取消'), (5, '超时取消'))
    status = models.SmallIntegerField(choices=status_choices, verbose_name="状态")
    order_type_choices = ((0, '用户下单'), (1, '线下班创建'),)
    order_type = models.SmallIntegerField(choices=order_type_choices, default=0, verbose_name="订单类型")
    date = models.DateTimeField(auto_now_add=True, verbose_name="订单生成时间")
    pay_time = models.DateTimeField(blank=True, null=True, verbose_name="付款时间")
    cancel_time = models.DateTimeField(blank=True, null=True, verbose_name="订单取消时间")

    def __str__(self):
        return "%s" % self.order_number


class OrderDetail(models.Model):
    """订单详情"""
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # 可关联普通课程或学位
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    original_price = models.FloatField("课程原价")
    price = models.FloatField("折后价格")
    content = models.CharField(max_length=255, blank=True, null=True)  # ？
    valid_period_display = models.CharField("有效期显示", max_length=32)  # 在订单页显示
    valid_period = models.PositiveIntegerField("有效期(days)")  # 课程有效期
    memo = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "%s - %s - %s" % (self.order, self.content_type, self.price)

    class Meta:
        # unique_together = ("order", 'course')
        unique_together = ("order", 'content_type', 'object_id')


######################################## 用户表 ########################################

from django.utils.safestring import mark_safe
from django.contrib.auth.models import AbstractUser


class UserInfo(AbstractUser):
    username = models.CharField("用户名", max_length=64, unique=True)
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        blank=True,
        null=True
    )
    uid = models.CharField(max_length=64, unique=True)  # 与第3方交互用户信息时，用这个uid,以避免泄露敏感用户信息
    mobile = models.BigIntegerField(verbose_name="手机", unique=True, help_text="用于手机验证码登录", null=True)
    qq = models.CharField(verbose_name="QQ", max_length=64, blank=True, null=True, db_index=True)
    weixin = models.CharField(max_length=128, blank=True, null=True, db_index=True, verbose_name="微信")
    signature = models.CharField('个人签名', blank=True, null=True, max_length=255)
    brief = models.TextField("个人介绍", blank=True, null=True)
    openid = models.CharField(max_length=128, blank=True, null=True)
    alipay_card = models.CharField(max_length=128, blank=True, null=True, verbose_name="支付宝账户")
    gender_choices = ((0, '保密'), (1, '男'), (2, '女'))
    gender = models.SmallIntegerField(choices=gender_choices, default=0, verbose_name="性别")
    id_card = models.CharField(max_length=32, blank=True, null=True, verbose_name="身份证号或护照号")
    password = models.CharField('password', max_length=128,
                                help_text=mark_safe('''<a class='btn-link' href='password'>重置密码</a>'''))
    is_active = models.BooleanField(default=True, verbose_name="账户状态")
    is_staff = models.BooleanField(verbose_name='staff status', default=False, help_text='决定着用户是否可登录管理后台')
    name = models.CharField(max_length=32, default="", verbose_name="真实姓名")
    head_img = models.CharField(max_length=256, default='/static/frontend/head_portrait/logo@2x.png',
                                verbose_name="个人头像")
    role_choices = ((0, '学员'), (1, '导师'), (2, '讲师'), (3, '管理员'), (4, '班主任'), (5, '线下班主任'))
    role = models.SmallIntegerField(choices=role_choices, default=0, verbose_name="角色")
    # balance = models.PositiveIntegerField(default=0, verbose_name="可提现余额")
    # #此处通过transaction_record表就可以查到，所以不用写在这了
    memo = models.TextField('备注', blank=True, null=True, default=None, help_text="json格式存储")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")
    beli = models.IntegerField(default=1000)

    class Meta:
        verbose_name = '用户信息'
        verbose_name_plural = "用户信息"

    def __str__(self):
        return "%s(%s)" % (self.username, self.get_role_display())


class Token(models.Model):
    """
    The default authorization token model.
    """
    key = models.CharField(max_length=40)
    user = models.OneToOneField(UserInfo, related_name='auth_token', on_delete=models.CASCADE, verbose_name="关联用户")
    created = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)

    def __str__(self):
        return self.key
