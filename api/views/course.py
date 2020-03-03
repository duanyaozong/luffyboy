from rest_framework.viewsets import ModelViewSet
from api.models import *
from api.utils.serializer import CourseSerializer, CourseDetailSerializer
from api.utils.auth import LoginAuth


class CourseView(ModelViewSet):
    authentication_classes = [LoginAuth]
    queryset = Course.objects.all()
    serializer_class = CourseSerializer


class CourseDetailView(ModelViewSet):
    authentication_classes = [LoginAuth]
    queryset = CourseDetail.objects.all()
    serializer_class = CourseDetailSerializer