# coding:utf-8
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from api.utils.auth import LoginAuth
from api.utils.response import BaseResponse
from api.utils.exceptions import CommonException
from api.models import *

import json
import redis

cache = redis.Redis(decode_responses=True)


class ShoppingCartView(APIView):
    authentication_classes = [LoginAuth]

    def post(self, request):
        '''
        状态码：
             1000： 成功
             1001： 课程不存在

        模拟请求数据：
        {
          "course_id":1,
          "price_policy_id":2
        }
        '''
        # 1 获取请求数据
        course_id = request.data.get('course_id')
        price_policy_id = request.data.get('price_policy_id')
        user_id = request.user.pk
        res = BaseResponse()

        try:
            # 2 校验数据
            # 2.1 校验课程是否存在
            course_obj = Course.objects.get(pk=course_id)
            # 2.2 校验价格策略是否合法
            price_policy_dict = {}
            for price_policy in course_obj.price_policy.all():
                price_policy_dict[price_policy.pk] = {
                    'pk': price_policy.pk,
                    'valid_period': price_policy.valid_period,
                    'valid_period_text': price_policy.get_valid_period_display(),
                    'price': price_policy.price,
                    'default': price_policy_id == price_policy.pk
                }
            if price_policy_id not in price_policy_dict:
                raise CommonException(1002, '价格策略错误！')
            pp = PricePolicy.objects.get(pk=price_policy_id)

            # 3 写入redis
            shoppingcart_key = settings.SHOPPINGCART_KEY%(user_id,course_id)
            shoppingcart_val = {
                'title': course_obj.name,
                'img': course_obj.course_img,
                'relate_price_policy': price_policy_dict,
                'choose_price_policy_id': price_policy_id,
                'price': pp.price,
                'valid_period': pp.valid_period,
                'valid_period_text': pp.get_valid_period_display()
            }

            cache.set(shoppingcart_key, json.dumps(shoppingcart_val))
            res.data = "加入购物车成功！"

            '''
            REDIS={
                  shoppingcart_1_1:{
                          "title":"....",
                          "img":"...."
                      }
                      
                  shoppingcart_1_2:{
                          "title":"....",
                          "img":"...."
                      }
            '''
        except CommonException as e:
            res.code = e.code
            res.msg = e.msg
        except ObjectDoesNotExist as e:
            res.code = 1001
            res.msg = "课程不存在"
        return Response(res.dict)

    '''
    1 post接口创建数据结构：
    {
        'title': 'Django课程',
        'img': 'https://www.luffycity.com/static/frontend/course/5/21å¤©_1544059695.5584881.jpeg',
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
    }


    2 get接口的数据结构：
        "data": {
            "total": 2,
            "shopping_cart_list": [
                {
                    "id": 2,
                    "default_price_period": 14,
                    "relate_price_policy": {
                        "1": {
                            "valid_period": 7,
                            "valid_period_text": "1周",
                            "default": false,
                            "prcie": 100
                        },
                        "2": {
                            "valid_period": 14,
                            "valid_period_text": "2周",
                            "default": true,
                            "prcie": 200
                        },
                        "3": {
                            "valid_period": 30,
                            "valid_period_text": "1个月",
                            "default": false,
                            "prcie": 300
                        }
                    },
                    "name": "Django框架学习",
                    "course_img": "https://luffycity.com/static/frontend/course/3/Django框架学习_1509095212.759272.png",
                    "default_price": 200
                },
                {
                    "id": 4,
                    "default_price_period": 30,
                    "relate_price_policy": {
                        "4": {
                            "valid_period": 30,
                            "valid_period_text": "1个月",
                            "default": true,
                            "prcie": 1000
                        },
                        "5": {
                            "valid_period": 60,
                            "valid_period_text": "2个月",
                            "default": false,
                            "prcie": 1500
                        }
                    },
                    "name": "Linux系统基础5周入门精讲",
                    "course_img": "https://luffycity.com/static/frontend/course/12/Linux5周入门_1509589530.6144893.png",
                    "default_price": 1000
                }]
            },
        "code": 1000,
        "msg": ""
    '''

    def get(self, request):
        res = BaseResponse()
        try:
            # 1 取到user_id
            user_id = request.user.id
            # 2 拼接购物车的key
            shoppingcart_key = settings.SHOPPINGCART_KEY%(user_id,'*')
            # shoppingcart_1_*
            # 3 去redis读取该用户的所有加入购物车的课程
            # 3.1 先去模糊匹配出所有符合要求的key
            all_keys = cache.scan_iter(shoppingcart_key)
            # 3.2 循环所有的keys得到每个key
            shoppingcart_list = []
            for key in all_keys:
                course_info = json.loads(cache.get(key))
                shoppingcart_list.append(course_info)

            res.data = {'shoppingcart_list':shoppingcart_list, 'total':len(shoppingcart_list)}
        except Exception as e:
            res.code = 1033
            res.error = '获取购物车失败'

        return Response(res.dict)

    def put(self, request):
        res = BaseResponse()
        try:
            # 1 获取course_id和price_policy_id
            course_id = request.data.get('course_id')
            price_policy_id = request.data.get('price_policy_id')
            user_id = request.user.id
            # 2 校验数据的合法性
            # 2.1 校验course_id是否合法
            shoppingcart_key = settings.SHOPPINGCART_KEY%(user_id,course_id)
            if not cache.exists(shoppingcart_key):
                res.code = 1035
                res.error = '课程不存在'
                return Response(res.dict)
            # 2.2 判断价格策略是否合法
            course_info = json.loads(cache.get(shoppingcart_key))
            price_policy_dict = course_info['relate_price_policy']
            if str(price_policy_id) not in price_policy_dict:
                res.code = 1036
                res.error = '所选的价格策略不存在'
                return Response(res.dict)
            # 3 修改redis中的default_policy_id
            course_info['choose_price_policy_id'] = price_policy_id
            # 4 修改信息后写入redis
            cache.set(shoppingcart_key,json.dumps(course_info))
            res.data = '更新成功'
        except Exception as e:
            res.code = 1034
            res.error = '更新价格策略失败'
        return Response(res.dict)

    def delete(self, request):
        res = BaseResponse()
        try:
            # 获取course_id
            course_id = request.data.get('course_id')
            user_id = request.user.id
            # 判断课程id是否合法
            shoppingcart_key = settings.SHOPPINGCART_KEY % (user_id,course_id)
            if not cache.exists(shoppingcart_key):
                res.code = 1039
                res.error = '删除的课程不存在'
                return Response(res.dict)
            # 删除redis中的数据
            cache.delete(shoppingcart_key)
            res.data = '删除成功'
        except Exception as e:
            res.code = 1037
            res.error = '删除失败'
        return Response(res.dict)
