# coding:utf-8
from rest_framework.views import APIView
from django.contrib import auth
from api.models import UserInfo, Token
from rest_framework.response import Response

import uuid
import datetime


class LoginView(APIView):
    def post(self, request):
        res = {'user': None, 'msg': None, 'token': None}
        try:
            #  获取数据
            user = request.data.get('user')
            pwd = request.data.get('pwd')
            print(user,pwd)
            user_obj = auth.authenticate(username=user, password=pwd)

            if user_obj:
                random_str = str(uuid.uuid4())
                Token.objects.update_or_create(user=user_obj, defaults={'key': random_str,
                                                                        'created': datetime.datetime.now()})
                res['user'] = user_obj.username
                res['token'] = random_str
            else:
                res['msg'] = "用户名或者密码错误！"

        except Exception as e:
            res['msg'] = str(e)

        return Response(res)

    # d025b041-3bce-4b94-b2d7-400ff1355c2c