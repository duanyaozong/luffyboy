# coding:utf-8
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from api.models import *
from api.utils.response import BaseResponse
from api.utils.exceptions import CommonException
from api.utils.auth import LoginAuth

import json
import redis
import datetime

cache = redis.Redis(decode_responses=True)


class AccountView(APIView):
    authentication_classes = [LoginAuth]

    # 获取优惠券列表
    def get_coupon_dict(self, request, course_id=None):
        now = datetime.datetime.now()
        coupon_record_list = CouponRecord.objects.filter(
            account=request.user,
            coupon__content_type=13,
            coupon__object_id=course_id,
            status=0,
            coupon__valid_begin_date__lte=now,
            coupon__valid_end_date__gte=now
        )
        coupons = {}
        for coupon_record in coupon_record_list:
            coupons[coupon_record.pk] = {
                'name': coupon_record.coupon.name,
                'coupon_type': coupon_record.coupon.coupon_type,
                'money_equivalent_value': coupon_record.coupon.money_equivalent_value,
                'off_percent': coupon_record.coupon.off_percent,
                'minimum_consume': coupon_record.coupon.minimum_consume
            }
        return coupons

    def post(self, request):
        '''
        状态码：
             1000： 成功
             1001： 课程不存在
        模拟请求数据：
        {
          "course_id_list":[1,2]
        }
        '''
        # 1 获取请求数据
        course_id_list = request.data.get('course_id_list')
        user_id = request.user.pk
        res = BaseResponse()
        try:
            # 结算情况： 1 直接购买 2 购物车结算
            # 2 创建数据结构
            # 清空操作，找到所有account_userid_*，全部清空
            del_list = cache.keys(settings.ACCOUNT_KEY%(user_id,'*'))
            if del_list:
                cache.delete(*del_list)

            price_list = []
            for course_id in course_id_list:
                # 结算key
                account_key = settings.ACCOUNT_KEY%(user_id,course_id)
                # 结算字典
                account_val = {}
                # 获取课程基本信息
                shoppingcart_key = settings.SHOPPINGCART_KEY%(user_id,course_id)

                # 判断课程是否存在购物车中
                if not cache.exists(shoppingcart_key):
                    raise CommonException('购物车不存在该课程',1040)

                course_obj = Course.objects.get(pk=course_id)
                course_info = json.loads(cache.get(shoppingcart_key))
                # 添加到结算字典中
                account_val['course_info'] = course_info

                # 课程价格加入到价格列表
                price_list.append(float(course_info['price']))

                # 获取优惠券信息:查询当前用户当前课程有效的未使用的优惠券
                coupons = self.get_coupon_dict(request, course_id)
                # 将优惠券字典添加到结算字典中
                account_val['coupons'] = coupons
                cache.set(account_key,json.dumps(account_val))

            # 获取通用优惠券
            global_coupons = self.get_coupon_dict(request)

            cache.set('global_coupons_%s'%user_id, json.dumps(global_coupons))
            cache.set('total_price',sum(price_list))

        except CommonException as e:
            res.code = e.code
            res.msg = e.msg
        except ObjectDoesNotExist as e:
            res.code = 1001
            res.msg = "课程不存在"

        return Response(res.dict)

    def get(self, request):
        res = BaseResponse()
        try:
            # 1 取到user_id
            user_id = request.user.id
            # 2 拼接account_key
            account_key = settings.ACCOUNT_KEY%(user_id, '*')
            # 3 去redis读取该用户的所有加入的课程
            # 3.1 先去模糊匹配出所有符合要求的key
            all_keys = cache.scan_iter(account_key)
            # 3.2 循环所有的keys得到每个key
            account_course_list = []
            for key in all_keys:
                course = json.loads(cache.get(key))
                temp = {}
                for key, val in course['course_info'].items():
                    temp[key] = val
                coupon_list = []
                for key, val in course['coupons'].items():
                    val['pk'] = key
                    coupon_list.append(val)
                temp['coupon_list'] = coupon_list

                account_course_list.append(temp)

            global_coupons_dict = json.loads(cache.get('global_coupons_%s' % user_id))
            total_price = cache.get('total_price')
            global_coupons = []
            for key, val in global_coupons_dict.items():
                global_coupons.append(val)
            res.data = {
                'account_course_list': account_course_list,
                'total': len(account_course_list),
                'global_coupons': global_coupons,
                'total_price': total_price
            }
        except Exception as e:
            res.code = 1033
            res.error = '获取购物车失败'
        return Response(res.dict)

    '''
account  1 post接口：
   account_1_1：{
        'course_info': {
            'title': 'Django课程',
            'img': 'https://www.luffycity.com/static/frontend/course/5/211544059695.5584881.jpeg',
            'relate_price_policy': {
                '1': {
                    'pk': 1,
                    'valid_period': 30,
                    'valid_period_text': '1个月',
                    'price': 1000.0,
                    'default': False
                },
                '2': {
                    'pk': 2,
                    'valid_period': 60,
                    'valid_period_text': '2个月',
                    'price': 2000.0,
                    'default': True
                },
                '3': {
                    'pk': 3,
                    'valid_period': 120,
                    'valid_period_text': '4个月',
                    'price': 3000.0,
                    'default': False
                }
            },
            'choose_price_policy_id': 2,
            'price': 2000.0,
            'valid_period': 60,
            'valid_period_text': '2个月'
        },
        'coupons': {
            '1': {
                'name': '双11百元立减券',
                'coupon_type': 0,
                'money_equivalent_value': 100.0,
                'off_percent': None,
                'minimum_consume': 0
            },
            '2': {
                'name': '双十二五折优惠券',
                'coupon_type': 2,
                'money_equivalent_value': 0.0,
                'off_percent': 50,
                'minimum_consume': 0
            }
        }
    } 
 
global_coupons_1：{
                '3': {
                    'name': 'alex大婚满减券',
                    'coupon_type': 1,
                    'money_equivalent_value': 50.0,
                    'off_percent': None,
                    'minimum_consume': 1000
                }
            }
2 get 接口
{
    'data':{
        'total':1,
        'total_price':200,
        'account_course_list':[
            {
                'id':2,
                'course_img'
                'default_price_period'
                'name'
                'default_price'
                'relate_price_policy':{
                    '1':{
                        'default':false
                        'valid_period_text'
                        'valid_period':7
                        'price':100
                    }
                    '2'{}
                },
                'coupon_list':[
                    {
                    'coupon_type':
                    'off_percent':null,
                    'valid_end_date'
                    'money_equivalent_value'
                    'valid_begin_date'
                    'name'
                    'minimum_consume'
                    'pk'
                    },
                    {}
                ]
            }
        ],
        'global_coupons':[
            {
                'coupon_type'
                'off_percent'
                'valid_end_date'
                'money_equivalent_value'
                'valid_begin_date'
                'name'
                'minimum_consume'
            }
        ]
    },
    'code':1000,
    'msg':''
}
'''

    def put(self, request):
        """
        # 更改优惠券信息
        choose_coupons:{
            choose_coupons:{'1':'2','2':'3','global_coupon_id':5}
            is_beli:true
        }
        """
        res = BaseResponse()
        try:
            # 获取数据
            choose_coupons = request.data.get('choose_coupons')
            is_beli = request.data.get('is_beli')
            user_pk = request.user.pk

            # 获取结算课程列表
            cal_price = {}
            data = self.get(request).data.get('data')
            account_course_list = data.get('account_course_list')
            account_course_info = {}
            for account_course in account_course_list:
                temp = {
                    'coupons': {},
                    'default_price':account_course['default_price']
                }
                account_course_info[account_course['id']] = temp

                for item in account_course['coupon_list']:
                    coupon_id = choose_coupons.get(str(account_course['id']))
                    if coupon_id == item['pk']:
                        temp['coupon'] = item

            price_list = []
            total_price = 0
            '''
               {
                    2: {
                        'coupon': {
                            'money_equivalent_value': 0.0,
                            'name': '清明节活动',
                            'pk': 3,
                            'off_percent': 80,
                            'coupon_type': '折扣券',
                            'minimum_consume': 0
                        },
                        'default_price': 200.0
                    }
                }
            '''
            for key, val in account_course_info.items():
                if not val.get('coupon'):
                    price_list.append(val['default_price'])
                    cal_price[key] = val['default_price']
                else:
                    coupon_info = val.get('coupon')
                    default_price = val['default_price']
                    # 计算折扣之后的价格
                    rebate_price = self.cal_coupon_price(default_price, coupon_info)
                    price_list.append(rebate_price)
                    cal_price[key] = rebate_price

            total_price = sum(price_list)

            # 计算通用优惠券的价格
            global_coupon_id = choose_coupons.get('global_coupon_id')
            if global_coupon_id:
                global_coupons = data.get('global_coupons')
                global_coupon_dict = {}
                for item in global_coupons:
                    global_coupon_dict[item['pk']] = item
                total_price = self.cal_coupon_price(total_price,global_coupon_dict[global_coupon_id])

            # 计算贝里
            if json.loads(is_beli):
                total_price = total_price - request.user.beli/10
                if total_price < 0:
                    total_price = 0

            cal_price['total_price'] = total_price
            res.data = cal_price
        except Exception as e:
            res.code = 500
            res.msg = "结算错误!"+str(e)

        return Response(res.dict)

    def cal_coupon_price(self, price, coupon_info):
        coupon_type = coupon_info['coupon_type']
        money_equivalent_value = coupon_info.get('money_equivalent_value')
        off_percent = coupon_info.get('off_percent')
        minimun_coupon = coupon_info.get('minimum_consume')
        rebate_price = 0
        if coupon_type == '立减券':
            rebate_price = price - money_equivalent_value
            if rebate_price <= 0:
                rebate_price = 0
        elif coupon_type == '满减券':
            if minimun_coupon > price:
                raise CommonException(3000,"优惠券未达到最低消费")
            else:
                rebate_price = price - money_equivalent_value
        elif coupon_type == "折扣券":
            rebate_price = price * off_percent/100

        return rebate_price


