from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import Faculty, Department, Course
from .serializers import FacultySerializer, DepartmentSerializer, CourseSerializer
from .retrieval import (
    retrieve_courses_full_text,
    retrieve_courses_trigram,
    retrieve_courses_hybrid,
    retrieve_departments_full_text,
    get_retrieval_context,
    format_context_for_llm
)


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

    @action(detail=False, methods=['post'])
    def search_full_text(self, request):
        query = request.data.get('query', '').strip()
        limit = request.data.get('limit', 10)
        
        if not query:
            return Response({
                'error': 'Query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            courses = retrieve_courses_full_text(query, limit=limit)
            serializer = self.get_serializer(courses, many=True)
            return Response({
                'method': 'full_text_search',
                'query': query,
                'count': len(courses),
                'results': serializer.data
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def search_trigram(self, request):
        query = request.data.get('query', '').strip()
        limit = request.data.get('limit', 10)
        
        if not query:
            return Response({
                'error': 'Query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            courses = retrieve_courses_trigram(query, limit=limit)
            serializer = self.get_serializer(courses, many=True)
            return Response({
                'method': 'trigram_search',
                'query': query,
                'count': len(courses),
                'results': serializer.data
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def search_hybrid(self, request):
        query = request.data.get('query', '').strip()
        limit = request.data.get('limit', 10)
        
        if not query:
            return Response({
                'error': 'Query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            courses = retrieve_courses_hybrid(query, limit=limit)
            serializer = self.get_serializer(courses, many=True)
            return Response({
                'method': 'hybrid_search',
                'query': query,
                'count': len(courses),
                'results': serializer.data
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def retrieve_context(self, request):
        query = request.data.get('query', '').strip()
        search_method = request.data.get('search_method', 'hybrid')
        
        if not query:
            return Response({
                'error': 'Query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            context = get_retrieval_context(query, search_method=search_method)
            formatted_context = format_context_for_llm(context)
            
            course_serializer = self.get_serializer(context['courses'], many=True)
            dept_serializer = DepartmentSerializer(context['departments'], many=True)
            
            return Response({
                'query': query,
                'search_method': search_method,
                'courses': course_serializer.data,
                'departments': dept_serializer.data,
                'university_info': [
                    {
                        'category': info.category,
                        'key': info.key,
                        'value': info.value
                    } for info in context['university_info']
                ],
                'formatted_context': formatted_context
            })
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

