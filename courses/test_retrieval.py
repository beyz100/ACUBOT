from django.test import TestCase
from courses.models import Faculty, Department, Course, UniversityInfo
from courses.retrieval import (
    retrieve_courses_full_text,
    retrieve_courses_trigram,
    retrieve_courses_hybrid,
    retrieve_departments_full_text,
    retrieve_university_info,
    get_retrieval_context,
    format_context_for_llm
)


class CourseRetrievalTestCase(TestCase):
    def setUp(self):
        self.faculty = Faculty.objects.create(name="Engineering Faculty")
        self.department = Department.objects.create(
            name="Computer Science",
            faculty=self.faculty
        )
        
        self.course1 = Course.objects.create(
            code="CS101",
            name="Introduction to Python Programming",
            ects=5,
            department=self.department
        )
        
        self.course2 = Course.objects.create(
            code="CS102",
            name="Data Structures and Algorithms",
            ects=6,
            department=self.department
        )
        
        self.course3 = Course.objects.create(
            code="MATH201",
            name="Linear Algebra",
            ects=5,
            department=self.department
        )
        
        self.university_info = UniversityInfo.objects.create(
            category='contact',
            key='Phone',
            value='+90 212 444 4444'
        )

    def test_retrieve_courses_full_text(self):
        results = retrieve_courses_full_text("Python Programming", limit=5)
        self.assertGreater(len(results), 0)
        self.assertIn(self.course1, results)

    def test_retrieve_courses_trigram(self):
        results = retrieve_courses_trigram("Python", limit=5)
        self.assertGreater(len(results), 0)

    def test_retrieve_courses_hybrid(self):
        results = retrieve_courses_hybrid("Programming", limit=5)
        self.assertGreater(len(results), 0)

    def test_retrieve_departments_full_text(self):
        results = retrieve_departments_full_text("Computer", limit=5)
        self.assertGreater(len(results), 0)
        self.assertIn(self.department, results)

    def test_retrieve_university_info(self):
        results = retrieve_university_info("Phone Contact", limit=5)
        self.assertGreater(len(results), 0)

    def test_get_retrieval_context(self):
        context = get_retrieval_context("Python Programming", search_method='hybrid')
        self.assertIn('courses', context)
        self.assertIn('departments', context)
        self.assertIn('university_info', context)
        self.assertIn('faculties', context)

    def test_format_context_for_llm(self):
        context = get_retrieval_context("Python", search_method='hybrid')
        formatted = format_context_for_llm(context)
        self.assertIsInstance(formatted, str)
        self.assertGreater(len(formatted), 0)

    def test_empty_query_results(self):
        results = retrieve_courses_full_text("xyzabc123nonexistent", limit=5)
        self.assertEqual(len(results), 0)

