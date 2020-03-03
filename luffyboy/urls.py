# coding:utf-8
"""
luffyboy URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from api.views.course import CourseView, CourseDetailView
from api.views.login import LoginView
from api.views.shoppingcart import ShoppingCartView
from api.views.account import AccountView
from api.views.payment import PaymentView

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^courses/$', CourseView.as_view({'get': 'list'})),
    url(r'^courses/detail/$', CourseDetailView.as_view({'get': 'list'})),
    url(r'^courses/detail/(?P<pk>\d+)/$', CourseDetailView.as_view({'get': 'retrieve'})),
    # 登录
    url(r'^login/$', LoginView.as_view()),
    # 购物车
    url(r'^shoppingcart/$', ShoppingCartView.as_view()),
    url(r'^account/$', AccountView.as_view()),
    url(r'^payment/$', PaymentView.as_view())
]
