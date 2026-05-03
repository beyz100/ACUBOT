#!/usr/bin/env python
"""
Test script to debug the language and retrieval issue.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courses.language import detect_language, expand_query
from courses.retrieval import retrieve, format_for_llm, _detect_department

# Test queries
queries = [
    "Tell me the courses of computer engineering",
    "Bilgisayar Mühendisliği bölümünün derslerini söyle"
]

for query in queries:
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")

    lang = detect_language(query)
    print(f"Detected Language: {lang}")

    expanded = expand_query(query)
    print(f"Expanded Query: {expanded}")

    department = _detect_department(query)
    print(f"Detected Department: {department}")

    result = retrieve(query)
    print(f"Retrieved Result:")
    print(f"  - Courses: {len(result.courses)}")
    print(f"  - Departments: {len(result.departments)}")
    print(f"  - Faculties: {len(result.faculties)}")
    print(f"  - University Info: {len(result.university_info)}")

    if result.courses:
        print(f"\nFirst 5 courses:")
        for c in result.courses[:5]:
            print(f"  - {c.code}: {c.name} / {c.name_en}")

    context = format_for_llm(result, lang)
    print(f"\nFormatted context length: {len(context)}")
    print(f"Context preview (first 200 chars):\n{context[:200]}...")

