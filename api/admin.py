# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from api.models import *

admin.site.register(Course)
admin.site.register(CourseDetail)
admin.site.register(Teacher)
admin.site.register(PricePolicy)
admin.site.register(Coupon)
admin.site.register(CouponRecord)

