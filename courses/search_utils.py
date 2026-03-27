from courses.retrieval import (
    get_retrieval_context,
    format_context_for_llm,
    retrieve_courses_full_text,
    retrieve_courses_trigram,
    retrieve_courses_hybrid
)


def search_and_display(query, search_method='hybrid'):
    print(f"\n{'='*60}")
    print(f"Search Query: {query}")
    print(f"Search Method: {search_method}")
    print(f"{'='*60}\n")
    
    if search_method == 'hybrid':
        courses = retrieve_courses_hybrid(query)
        print(f"Hybrid Search Results ({len(courses)} courses found):")
    elif search_method == 'full_text':
        courses = retrieve_courses_full_text(query)
        print(f"Full-Text Search Results ({len(courses)} courses found):")
    elif search_method == 'trigram':
        courses = retrieve_courses_trigram(query)
        print(f"Trigram Search Results ({len(courses)} courses found):")
    else:
        courses = retrieve_courses_hybrid(query)
        print(f"Default Hybrid Search Results ({len(courses)} courses found):")
    
    for idx, course in enumerate(courses, 1):
        print(f"\n{idx}. {course.code} - {course.name}")
        print(f"   ECTS: {course.ects}")
        print(f"   Department: {course.department.name}")
        print(f"   Faculty: {course.department.faculty.name}")


def get_context_and_display(query, search_method='hybrid'):
    print(f"\n{'='*60}")
    print(f"Context Retrieval Query: {query}")
    print(f"Search Method: {search_method}")
    print(f"{'='*60}\n")
    
    context = get_retrieval_context(query, search_method=search_method)
    formatted = format_context_for_llm(context)
    
    print(formatted)
    
    return context


if __name__ == '__main__':
    import django
    import os
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    search_and_display("Python Programming", search_method='hybrid')
    search_and_display("Data Structures", search_method='full_text')
    search_and_display("Algoritma", search_method='trigram')
    
    get_context_and_display("Introduction to Programming", search_method='hybrid')

