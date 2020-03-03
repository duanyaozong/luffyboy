from rest_framework import serializers
from api.models import *


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

    level = serializers.CharField(source='get_level_display')
    coursedetail_id = serializers.CharField(source='coursedetail.pk')


class CourseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseDetail
        fields = '__all__'

    name = serializers.CharField(source='course.name')
    prices = serializers.SerializerMethodField()
    brief = serializers.CharField(source='course.brief')
    study_all_time = serializers.StringRelatedField(source='hours')
    level = serializers.CharField(source='course.get_level_display')
    teachers = serializers.SerializerMethodField()
    is_online = serializers.CharField(source='course.get_status_display')
    recommend_coursesinfo = serializers.SerializerMethodField()

    def get_prices(self, instance):
        return [{'price': obj.price,
                 'valid_period': obj.valid_period,
                 'valid_period_text': obj.get_valid_period_display()}
                for obj in instance.course.price_policy.all()]

    def get_teachers(self, instance):
        return [{'name': obj.name,
                 'image': obj.image} for obj in instance.teachers.all()]

    def get_recommend_coursesinfo(self, instance):
        return [{'name': obj.name,
                 'pk': obj.pk} for obj in instance.recommend_courses.all()]