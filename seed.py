import os
import sys
import json
import argparse
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from courses.models import Faculty, Department, Course, UniversityInfo


DATA_DIR = Path(__file__).resolve().parent / 'courses' / 'data'


def _load_json(filename):
    path = DATA_DIR / filename
    if not path.exists():
        print(f"  ⚠  Dosya bulunamadı: {path}")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def seed_faculties(flush=False):
    print("\n" + "=" * 60)
    print("🏛  Fakülteleri Yükleme")
    print("=" * 60)

    if flush:
        deleted, _ = Faculty.objects.all().delete()
        print(f"  🗑  Mevcut fakülteler silindi: {deleted}")

    rows = _load_json('faculties.json')
    if rows is None:
        return {}

    by_name = {}
    added = 0
    updated = 0
    for item in rows:
        faculty, created = Faculty.objects.update_or_create(
            name=item['name'],
            defaults={
                'name_en': item.get('name_en', ''),
                'description': item.get('description', ''),
                'website': item.get('website', ''),
            },
        )
        by_name[faculty.name] = faculty
        if created:
            print(f"  ✅  Eklendi: {faculty.name}")
            added += 1
        else:
            updated += 1

    print(f"\n  📊  Sonuç: {added} yeni, {updated} güncellendi.")
    return by_name


def seed_departments(faculties, flush=False):
    print("\n" + "=" * 60)
    print("🏫  Bölümleri Yükleme")
    print("=" * 60)

    if flush:
        deleted, _ = Department.objects.all().delete()
        print(f"  🗑  Mevcut bölümler silindi: {deleted}")

    rows = _load_json('departments.json')
    if rows is None:
        return {}

    by_name = {}
    added = 0
    updated = 0
    skipped = 0
    for item in rows:
        faculty = faculties.get(item['faculty'])
        if faculty is None:
            print(f"  ⚠  Atlandı: '{item['name']}' — bilinmeyen fakülte '{item['faculty']}'")
            skipped += 1
            continue
        dept, created = Department.objects.update_or_create(
            faculty=faculty,
            name=item['name'],
            defaults={
                'name_en': item.get('name_en', ''),
                'description': item.get('description', ''),
                'program_url': item.get('program_url', ''),
            },
        )
        by_name[dept.name] = dept
        if created:
            print(f"  ✅  Eklendi: {dept.name} ({faculty.name})")
            added += 1
        else:
            updated += 1

    print(f"\n  📊  Sonuç: {added} yeni, {updated} güncellendi, {skipped} atlandı.")
    return by_name


def seed_courses(departments, flush=False):
    print("\n" + "=" * 60)
    print("📚  Dersleri Yükleme")
    print("=" * 60)

    if flush:
        deleted, _ = Course.objects.all().delete()
        print(f"  🗑  Mevcut dersler silindi: {deleted}")

    rows = _load_json('courses.json')
    if rows is None:
        return

    added = 0
    updated = 0
    skipped = 0
    for item in rows:
        dept = departments.get(item['department'])
        if dept is None:
            skipped += 1
            continue
        _, created = Course.objects.update_or_create(
            department=dept,
            code=item['code'],
            defaults={
                'name': item['name'],
                'name_en': item.get('name_en', ''),
                'ects': int(item.get('ects', 0)),
                'semester': item.get('semester'),
                'description': item.get('description', ''),
            },
        )
        if created:
            added += 1
        else:
            updated += 1

    print(f"\n  📊  Sonuç: {added} yeni, {updated} güncellendi, {skipped} atlandı.")


def seed_university_info(flush=False):
    print("\n" + "=" * 60)
    print("🏛  Üniversite Genel Bilgilerini Yükleme")
    print("=" * 60)

    if flush:
        deleted, _ = UniversityInfo.objects.all().delete()
        print(f"  🗑  Mevcut üniversite bilgileri silindi: {deleted}")

    rows = _load_json('university_info.json')
    if rows is None:
        return

    added = 0
    updated = 0
    for item in rows:
        _, created = UniversityInfo.objects.update_or_create(
            category=item['category'],
            key=item['key'],
            defaults={
                'value': item['value'],
                'keywords': item.get('keywords', ''),
            },
        )
        if created:
            print(f"  ✅  Eklendi: [{item['category']}] {item['key']}")
            added += 1
        else:
            updated += 1

    print(f"\n  📊  Sonuç: {added} yeni, {updated} güncellendi.")


def seed_scraper_data():
    scraper_path = Path(__file__).resolve().parent / 'acibadem_data.json'
    if not scraper_path.exists():
        return
    with open(scraper_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    contact_info = data.get("contact_info", {})
    if "bilgisayar_muhendisligi_bolum_baskani" in contact_info:
        UniversityInfo.objects.update_or_create(
            category="academic",
            key="computer_engineering_head",
            defaults={
                "value": f"Bilgisayar Mühendisliği Bölüm Başkanı: {contact_info['bilgisayar_muhendisligi_bolum_baskani']}",
                "keywords": "bilgisayar mühendisliği başkanı, computer engineering head, department head",
            }
        )
        print("  ✅  Scraper'dan Bilgisayar Müh. Bölüm Başkanı güncellendi.")


def run_seeder(only_courses=False, only_university=False, flush=False):
    print("\n🚀  ACU ChatBot — Data Pipeline başlatılıyor...")

    if not only_university:
        faculties = seed_faculties(flush=flush)
        departments = seed_departments(faculties, flush=flush)
        seed_courses(departments, flush=flush)

    if not only_courses:
        seed_university_info(flush=flush)
        seed_scraper_data()

    print("\n" + "=" * 60)
    print("✨  Data Pipeline tamamlandı!")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ACU ChatBot — Veritabanı seed scripti'
    )
    parser.add_argument(
        '--only-courses', action='store_true',
        help='Sadece fakülte/bölüm/ders verilerini yükle'
    )
    parser.add_argument(
        '--only-university', action='store_true',
        help='Sadece üniversite genel bilgilerini yükle'
    )
    parser.add_argument(
        '--flush', action='store_true',
        help='Mevcut verileri silip baştan yükle'
    )

    args = parser.parse_args()
    run_seeder(
        only_courses=args.only_courses,
        only_university=args.only_university,
        flush=args.flush,
    )
