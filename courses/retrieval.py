from django.db.models import Q, Value, CharField, F, FloatField
from django.db.models.functions import Coalesce, Cast, Length
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity
from courses.models import Course, Faculty, Department, UniversityInfo


def retrieve_courses_full_text(query, limit=10):
    search_query = SearchQuery(query, search_type='websearch')
    
    search_vector = SearchVector('code', weight='A') + \
                    SearchVector('name', weight='B') + \
                    SearchVector('department__name', weight='C')
    
    courses = Course.objects.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, search_query)
    ).filter(
        search=search_query
    ).select_related('department__faculty').order_by('-rank')[:limit]
    
    return list(courses)


def retrieve_courses_trigram(query, limit=10):
    courses = Course.objects.annotate(
        name_similarity=TrigramSimilarity('name', query),
        code_similarity=TrigramSimilarity('code', query)
    ).filter(
        Q(name_similarity__gt=0.1) | Q(code_similarity__gt=0.1)
    ).select_related('department__faculty').order_by('-name_similarity', '-code_similarity')[:limit]
    
    return list(courses)


def retrieve_courses_hybrid(query, limit=10):
    try:
        full_text_courses = retrieve_courses_full_text(query, limit=limit)
        full_text_ids = {course.id for course in full_text_courses}
    except:
        full_text_courses = []
        full_text_ids = set()
    
    trigram_courses = retrieve_courses_trigram(query, limit=limit)
    trigram_ids = {course.id for course in trigram_courses}
    
    hybrid_ids = full_text_ids | trigram_ids
    
    if not hybrid_ids:
        return []
    
    all_courses = Course.objects.filter(
        id__in=hybrid_ids
    ).select_related('department__faculty')
    
    scored_courses = []
    for course in all_courses:
        score = 0
        if course.id in full_text_ids:
            score += 2
        if course.id in trigram_ids:
            score += 1
        scored_courses.append((course, score))
    
    scored_courses.sort(key=lambda x: x[1], reverse=True)
    return [course for course, score in scored_courses[:limit]]


def retrieve_university_info(query, limit=5):
    search_query = SearchQuery(query, search_type='websearch')
    
    search_vector = SearchVector('key', weight='A') + \
                    SearchVector('value', weight='B') + \
                    SearchVector('category', weight='C')
    
    info = UniversityInfo.objects.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, search_query)
    ).filter(
        search=search_query
    ).order_by('-rank')[:limit]
    
    return list(info)


def retrieve_departments_full_text(query, limit=10):
    search_query = SearchQuery(query, search_type='websearch')
    
    search_vector = SearchVector('name', weight='A') + \
                    SearchVector('faculty__name', weight='B')
    
    departments = Department.objects.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, search_query)
    ).filter(
        search=search_query
    ).select_related('faculty').order_by('-rank')[:limit]
    
    return list(departments)


def retrieve_faculties_full_text(query, limit=10):
    search_query = SearchQuery(query, search_type='websearch')
    
    search_vector = SearchVector('name', weight='A')
    
    faculties = Faculty.objects.annotate(
        search=search_vector,
        rank=SearchRank(search_vector, search_query)
    ).filter(
        search=search_query
    ).order_by('-rank')[:limit]
    
    return list(faculties)


def retrieve_combined_context(query, limit=15):
    courses = retrieve_courses_hybrid(query, limit=5)
    departments = retrieve_departments_full_text(query, limit=3)
    university_info = retrieve_university_info(query, limit=2)
    
    context = {
        'courses': courses,
        'departments': departments,
        'university_info': university_info,
    }
    
    return context


def format_context_for_llm(context):
    formatted = "Retrieved Context Information:\n\n"
    
    if context['courses']:
        formatted += "Relevant Courses:\n"
        for course in context['courses']:
            formatted += f"- Code: {course.code}, Name: {course.name}, ECTS: {course.ects}, Department: {course.department.name}, Faculty: {course.department.faculty.name}\n"
        formatted += "\n"
    
    if context['departments']:
        formatted += "Relevant Departments:\n"
        for dept in context['departments']:
            formatted += f"- Name: {dept.name}, Faculty: {dept.faculty.name}\n"
        formatted += "\n"
    
    if context['university_info']:
        formatted += "University Information:\n"
        for info in context['university_info']:
            formatted += f"- [{info.category}] {info.key}: {info.value}\n"
        formatted += "\n"
    
    return formatted


def get_retrieval_context(user_query, search_method='hybrid'):
    if search_method == 'hybrid':
        courses = retrieve_courses_hybrid(user_query)
    elif search_method == 'full_text':
        courses = retrieve_courses_full_text(user_query)
    elif search_method == 'trigram':
        courses = retrieve_courses_trigram(user_query)
    else:
        courses = retrieve_courses_hybrid(user_query)
    
    departments = retrieve_departments_full_text(user_query, limit=3)
    university_info = retrieve_university_info(user_query, limit=2)
    faculties = retrieve_faculties_full_text(user_query, limit=2)
    
    context = {
        'courses': courses,
        'departments': departments,
        'university_info': university_info,
        'faculties': faculties,
    }
    
    return context

