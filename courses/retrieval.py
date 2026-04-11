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
        code_similarity=TrigramSimilarity('code', query),
        dept_similarity=TrigramSimilarity('department__name', query)
    ).filter(
        Q(name_similarity__gt=0.15) | Q(code_similarity__gt=0.2) | Q(dept_similarity__gt=0.15)
    ).select_related('department__faculty').order_by('-name_similarity', '-code_similarity', '-dept_similarity')[:limit]

    return list(courses)


def retrieve_courses_by_department(department_query, limit=20):
    departments = Department.objects.annotate(
        dept_sim=TrigramSimilarity('name', department_query)
    ).filter(
        dept_sim__gt=0.2  
    ).order_by('-dept_sim')
    
    if not departments:
        return []
    
    matched_dept_ids = [d.id for d in departments[:3]]  
    courses = Course.objects.filter(
        department_id__in=matched_dept_ids
    ).select_related('department__faculty').order_by('code')[:limit]
    
    return list(courses)


def retrieve_courses_hybrid(query, limit=50):
    dept_courses = retrieve_courses_by_department(query, limit=limit)
    if dept_courses:
        return dept_courses
    try:
        full_text_courses = retrieve_courses_full_text(query, limit=limit*2)
        full_text_ids = {course.id for course in full_text_courses}
    except:
        full_text_courses = []
        full_text_ids = set()
    
    trigram_courses = retrieve_courses_trigram(query, limit=limit*2)
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
            score += 3
        if course.id in trigram_ids:
            score += 1
        scored_courses.append((course, score))
    
    scored_courses.sort(key=lambda x: (-x[1], x[0].code))
    return [course for course, score in scored_courses[:limit]]


def retrieve_university_info(query, limit=5):
    info = UniversityInfo.objects.annotate(
        key_sim=TrigramSimilarity('key', query),
        val_sim=TrigramSimilarity('value', query),
        cat_sim=TrigramSimilarity('category', query)
    ).filter(
        Q(key_sim__gt=0.2) | Q(val_sim__gt=0.2) | Q(cat_sim__gt=0.15)
    ).order_by('-val_sim', '-key_sim')[:limit]
    
    if not info:
        info = UniversityInfo.objects.filter(category='contact')[:limit]
        
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
    formatted = ""
    
    if context.get('courses'):
        formatted += "Courses:\n"
        for course in context['courses']:
            formatted += f"- {course.code} {course.name} (Dept: {course.department.name})\n"
        formatted += "\n"
        
    if context.get('departments'):
        formatted += "Departments:\n"
        for dept in context['departments']:
            formatted += f"- {dept.name} (Faculty: {dept.faculty.name})\n"
        formatted += "\n"
        
    if context.get('university_info'):
        formatted += "University Info:\n"
        for info in context['university_info']:
            formatted += f"- {info.key}: {info.value}\n"
        formatted += "\n"

    if context.get('faculties'):
        formatted += "Faculties:\n"
        for faculty in context['faculties']:
            formatted += f"- {faculty.name}\n"
    
    return formatted.strip()


def get_retrieval_context(user_query, search_method='hybrid'):
    if search_method == 'hybrid':
        courses = retrieve_courses_hybrid(user_query, limit=50)
    elif search_method == 'full_text':
        courses = retrieve_courses_full_text(user_query, limit=50)
    elif search_method == 'trigram':
        courses = retrieve_courses_trigram(user_query, limit=50)
    else:
        courses = retrieve_courses_hybrid(user_query, limit=50)
    
    departments = retrieve_departments_full_text(user_query, limit=10)
    university_info = retrieve_university_info(user_query, limit=30)
    faculties = retrieve_faculties_full_text(user_query, limit=20)
    
    context = {
        'courses': courses,
        'departments': departments,
        'university_info': university_info,
        'faculties': faculties,
    }
    
    return context
