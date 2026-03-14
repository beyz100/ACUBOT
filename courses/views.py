from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from .models import Faculty, Department, Course
from .serializers import FacultySerializer, DepartmentSerializer, CourseSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class FacultyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    pagination_class = StandardResultsSetPagination


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Department.objects.select_related('faculty')
    serializer_class = DepartmentSerializer
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['faculty']
    search_fields = ['name']


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.objects.select_related('department')
    serializer_class = CourseSerializer
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['department', 'code']
    search_fields = ['name', 'code']
