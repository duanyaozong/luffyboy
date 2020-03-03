# coding:utf-8
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from api.models import Token
import datetime
from django.core.cache import cache
import pytz


class LoginAuth(BaseAuthentication):
    def authenticate(self, request):
        '''
        1 对token设置14天有效时间
        2 缓存存储
        '''
        # 从请求头部获取token
        token = request.META.get('HTTP_AUTHORIZATION')
        # 1 校验是否存在token字符串
        # 1.1 缓存校验
        user = cache.get(token)
        if user:
            return user, token
        # 1.2 数据库校验
        token_obj = Token.objects.filter(key=token).first()
        if not token_obj:
            raise AuthenticationFailed("认证失败！")

        # 2 校验是否在有效期内
        now = datetime.datetime.now()
        now = now.replace(tzinfo=pytz.timezone('UTC'))
        delta = now - token_obj.created
        state = delta < datetime.timedelta(weeks=2)
        if state:
            # 校验成功，写入缓存中
            delta = datetime.timedelta(weeks=2) - delta
            cache.set(token_obj.key, token_obj.user, min(delta.total_seconds(),3600*24*7))
            return token_obj.user, token_obj.key
        else:
            raise AuthenticationFailed("认证超时！")