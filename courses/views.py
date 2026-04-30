from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import Faculty, Department, Course
from .serializers import FacultySerializer, DepartmentSerializer, CourseSerializer
from .retrieval import retrieve, format_for_llm


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
    def search(self, request):
        """Run the same hybrid retrieval used by the chatbot.

        Body: {"query": "..."}
        Returns courses, departments, faculties, university info — and the
        plain-text formatted context that gets fed to the LLM."""
        query = (request.data.get('query') or '').strip()
        if not query:
            return Response(
                {'error': 'Query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = retrieve(query)
        except Exception as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        course_serializer = self.get_serializer(result.courses, many=True)
        dept_serializer = DepartmentSerializer(result.departments, many=True)
        faculty_serializer = FacultySerializer(result.faculties, many=True)
        return Response({
            'query': query,
            'count': result.total(),
            'matched_department': result.matched_department.name if result.matched_department else None,
            'matched_faculty': result.matched_faculty.name if result.matched_faculty else None,
            'courses': course_serializer.data,
            'departments': dept_serializer.data,
            'faculties': faculty_serializer.data,
            'university_info': [
                {
                    'category': info.category,
                    'key': info.key,
                    'value': info.value,
                } for info in result.university_info
            ],
            'formatted_context': format_for_llm(result, language='en'),
        })
