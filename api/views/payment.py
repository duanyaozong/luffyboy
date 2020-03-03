# coding:utf-8
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from api.utils.auth import LoginAuth
from django.core.exceptions import ObjectDoesNotExist
from api.utils.response import BaseResponse
from api.models import *
from api.utils.exceptions import CommonException
# from api.utils.ali.api import ali_api

import random, datetime, time, os, sys
import redis
from django.conf import settings

cache = redis.Redis(decode_responses=True)


class PaymentView(APIView):
    '''
        模拟请求数据格式：
            {
            is_beli:true,
            course_list=[
                  {  course_id:1
                   default_price_policy_id:1,
                   coupon_record_id:2
                   },
                  { course_id:2
                   default_price_policy_id:4,
                   coupon_record_id:6
                   }
                 ],
            global_coupon_id:3,
            pay_money:298
           }

        状态码：
             1000:  成功
             1001:  课程不存在
             1002:  价格策略不合法
             1003:  加入购物车失败
             1004:  获取购物车失败
             1005:  贝里数有问题
             1006:  优惠券异常
             1007:  优惠券未达到最低消费
             1008:  支付总价格异常
        '''
    authentication_classes = [LoginAuth]

    def post(self, request):
        res = BaseResponse()
        # 1 获取数据
        user_id = request.user.pk
        global_coupon_id = request.data.get('global_coupon_id')
        pay_money = request.data.get('pay_money')
        course_list = request.data.get('course_list')
        is_beli = request.data.get('is_beli')
        now = datetime.datetime.now()

        try:
            # 2 校验数据
            # 2.1 校验课程
            course_price_list = []
            for course_dict in course_list:
                # 校验课程id
                course_id = course_dict.get('course_id')
                course_obj = Course.objects.get(pk=course_id)
                # 价格策略id
                if course_dict.get('default_price_id') not in [obj.pk for obj in course_obj.price_policy.all()]:
                    raise CommonException("价格策略异常！", 1002)
                # 课程优惠券id
                price_policy_obj = PricePolicy.objects.get(pk=course_dict.get('default_price_policy_id'))
                course_dict['original_price'] = price_policy_obj.price
                course_dict['valid_period_display'] = price_policy_obj.get_valid_period_display
                course_dict['valid_period'] = price_policy_obj.valid_period
                coupon_record_id = course_dict.get('coupon_record_id')

                if coupon_record_id:
                    coupon_record_list = CouponRecord.objects.filter(
                        account = request.user,
                        status = 0,
                        coupon__valid_begin_date__lt = now,
                        coupon__valid_end_date__gt = now,
                        coupon__content_type_id = 13,
                        coupon__object_id = course_id
                    )

                    if coupon_record_list and coupon_record_id not in [obj.pk for obj in coupon_record_list]:
                        raise CommonException("课程优惠券异常！", 1006)

                    # 计算循环课程的课程优惠券优惠后的价格
                    coupon_record_obj = CouponRecord.objects.get(pk=coupon_record_id)
                    rebate_price = self.cal_coupon_price(price_policy_obj.price, coupon_record_obj)
                    course_price_list.append(rebate_price)
                    course_dict['rebate_price'] = rebate_price
                else:
                    course_price_list.append(price_policy_obj.price)

            # 2.2 校验通用优惠券id
            if global_coupon_id:
                global_coupon_record_list = CouponRecord.objects.filter(
                    account = request.user,
                    status = 0,
                    coupon__valid_begin_date__lt = now,
                    coupon__valid_end_date__gt = now,
                    coupon__content_type_id = 13,
                    coupon__object_id = None
                )
                if global_coupon_record_list and global_coupon_id not in [obj.pk for obj in global_coupon_record_list]:
                    raise CommonException("通用优惠券异常", 1006)

                global_coupon_record_obj = CouponRecord.objects.get(pk=global_coupon_id)
                final_price = self.cal_coupon_price(sum(course_price_list), global_coupon_record_obj)
            else:
                final_price = sum(course_price_list)
            # 2.3 计算实际支付价格与money做校验
            cost_beli_num = 0
            if is_beli:
                price = final_price - request.user.beli / 10
                cost_beli_num = request.user.beli
                if price < 0:
                    price = 0
                    cost_beli_num = final_price * 10
                final_price = price

            if final_price != float(pay_money):
                raise CommonException(1008, "支付总价格异常！")

            # 3 生成订单记录
            order_number = self.get_order_num()
            order_obj = Order.objects.create(
                payment_type = 1,
                order_number = order_number,
                account = request.user,
                status = 1,
                order_type = 1,
                actual_amount = pay_money
            )

            for course_item in course_list:
                OrderDetail.objects.create(
                    order = order_obj,
                    content_type_id = 7,
                    object_id = course_item.get('course_id'),
                    original_price = course_item.get('original_price'),
                    price = course_item.get('rebate_price') or course_item.get('original_price'),
                    valid_period = course_item.get('valid_period'),
                    valid_period_display = course_item.get('valid_period_display')
                )
                
            request.user.beli = request.user.beli - cost_beli_num
            request.user.save()
            cache.set(order_number+'|'+str(cost_beli_num),'',20)
            account_key = settings.ACCOUNT_KEY%(user_id,"*")
            cache.delete(*cache.keys(account_key))
            '''
              [
                 {  course_id:1
                    default_price_policy_id:1,
                    coupon_record_id:2
                  },
                 {
                    course_id:2
                    default_price_policy_id:4,
                    coupon_record_id:6
                  }
              ]
            '''
            res.data = self.get_pay_url(request, order_number, final_price)
        except ObjectDoesNotExist as e:
            res.code = 1001
            res.msg = "课程不存在！"
        except CommonException as e:
            res.code = e.code
            res.msg = e.msg
        except Exception as e:
            res.code = 500
            res.msg = str(e)

        return Response(res.dict)
