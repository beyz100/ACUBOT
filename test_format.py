#!/usr/bin/env python
"""
Test script to verify course formatting with categorization.
Shows how courses will be displayed to the LLM.
"""

import json

# Sample data
courses_data = [
    {"code": "CHE 101", "name": "Genel Kimya"},
    {"code": "CSE 101", "name": "Programlamaya Giriş"},
    {"code": "ENG 105", "name": "Akademik Amaçlar için İngilizce I"},
    {"code": "MAT 111", "name": "Kalkülüs I"},
    {"code": "PHY 101", "name": "Fizik I"},
    {"code": "TUR 101", "name": "Türk Dili I"},
    {"code": "CSE 220", "name": "Web Programlama"},
    {"code": "CSE 301", "name": "Bilgisayar Mimarisi"},
    {"code": "ACU 2001", "name": "Seçmeli Ders"},
    {"code": "ACU 2002", "name": "Seçmeli Ders"},
    {"code": "ADS 4001", "name": "Genel Seçmeli"},
    {"code": "CSE 4001", "name": "Teknik Seçmeli"},
]

print("=" * 80)
print("ESKI FORMAT (VERBOSE)")
print("=" * 80)

formatted_old = "Courses:\n"
for course in courses_data:
    formatted_old += f"- {course['code']}: {course['name']} (X ECTS)\n"

print(formatted_old)
print(f"Karakter sayısı: {len(formatted_old)}\n\n")

print("=" * 80)
print("YENİ FORMAT (KATEGORIZE EDİLMİŞ)")
print("=" * 80)

mandatory_courses = []
elective_courses = []
general_electives = []
technical_electives = []

for course in courses_data:
    course_line = f"{course['code']} {course['name']}"

    if "Seçmeli" in course['name'] and "Genel" in course['name']:
        general_electives.append(course_line)
    elif "Teknik Seçmeli" in course['name'] or course['code'].startswith("CSE 4"):
        technical_electives.append(course_line)
    elif "Seçmeli" in course['name'] or course['code'].startswith("ACU"):
        elective_courses.append(course_line)
    else:
        mandatory_courses.append(course_line)

formatted_new = "Courses:\n"

if mandatory_courses:
    for line in mandatory_courses:
        formatted_new += f"• {line}\n"

if elective_courses:
    formatted_new += "Electives: " + ", ".join(elective_courses) + "\n"

if general_electives:
    formatted_new += "General Electives: " + ", ".join(general_electives) + "\n"

if technical_electives:
    formatted_new += "Technical Electives: " + ", ".join(technical_electives) + "\n"

print(formatted_new)
print(f"Karakter sayısı: {len(formatted_new)}\n")

print("=" * 80)
print("KARŞILAŞTIRMA")
print("=" * 80)

print(f"Eski format: {len(formatted_old)} karakter")
print(f"Yeni format: {len(formatted_new)} karakter")
print(f"Tasarruf: {len(formatted_old) - len(formatted_new)} karakter ({100 * (len(formatted_old) - len(formatted_new)) / len(formatted_old):.1f}% azalış)")
print(f"\n✅ Seçmeli dersler tek satırda gösteriliyor")
print(f"✅ Genel Seçmeli dersleri ayrı kategoride")
print(f"✅ Daha az karakter = Daha fazla dersi sığdırabilir")

