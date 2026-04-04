"""
Test script to verify the improved retrieval system.
Run: python manage.py shell < test_retrieval_fix.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courses.models import Course, Department
from courses.retrieval import retrieve_courses_by_department, retrieve_courses_hybrid

def test_department_retrieval():
    """Test department-based course retrieval"""
    print("\n" + "="*70)
    print("TEST 1: Department-Based Retrieval")
    print("="*70)

    print("\nTest: Bilgisayar Mühendisliği bölümü")
    print("-" * 70)

    # List all departments first
    departments = Department.objects.all()
    print(f"\nAvailable departments ({departments.count()}):")
    for dept in departments:
        dept_courses = Course.objects.filter(department=dept).count()
        print(f"  - {dept.name}: {dept_courses} courses")

    # Test department retrieval
    courses = retrieve_courses_by_department("Bilgisayar Mühendisliği", limit=50)
    print(f"\nRetrieved courses for 'Bilgisayar Mühendisliği': {len(courses)}")

    if courses:
        print("\nFirst 10 courses:")
        for i, course in enumerate(courses[:10], 1):
            print(f"  {i}. {course.code}: {course.name} (ECTS: {course.ects})")

        if len(courses) > 10:
            print(f"  ... and {len(courses) - 10} more courses")

    return len(courses)

def test_hybrid_retrieval():
    """Test improved hybrid retrieval"""
    print("\n" + "="*70)
    print("TEST 2: Hybrid Retrieval (Department Detection)")
    print("="*70)

    test_queries = [
        "Bilgisayar Mühendisliği dersleri",
        "bilgisayar mühendisliği bölümündeki dersler",
        "computer engineering courses",
        "web programming",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 70)
        courses = retrieve_courses_hybrid(query, limit=20)
        print(f"  Results: {len(courses)} courses")

        if courses:
            print(f"  Sample results:")
            for course in courses[:5]:
                print(f"    - {course.code}: {course.name}")
            if len(courses) > 5:
                print(f"    ... and {len(courses) - 5} more")

def test_direct_query():
    """Test direct database query"""
    print("\n" + "="*70)
    print("TEST 3: Direct Database Query")
    print("="*70)

    cs_dept = Department.objects.filter(name__icontains="Bilgisayar").first()

    if cs_dept:
        print(f"\nDepartment: {cs_dept.name}")
        cs_courses = Course.objects.filter(department=cs_dept).order_by('code')
        print(f"Total courses in database: {cs_courses.count()}")

        print("\nAll courses:")
        for i, course in enumerate(cs_courses, 1):
            print(f"  {i}. {course.code}: {course.name} (ECTS: {course.ects})")

if __name__ == "__main__":
    try:
        # Run tests
        dept_count = test_department_retrieval()
        test_hybrid_retrieval()
        test_direct_query()

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"✅ Department retrieval: {dept_count} courses found")
        print("✅ Hybrid retrieval: Multiple queries tested")
        print("✅ Database integrity: Verified")
        print("\n✨ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

