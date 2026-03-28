import os
import sys
import json
import argparse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from courses.models import Faculty, Department, Course, UniversityInfo


def _load_json(file_path):
    if not os.path.exists(file_path):
        print(f"  ⚠  Dosya bulunamadı: {file_path}")
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def seed_bologna_courses(flush=False):
    print("\n" + "=" * 60)
    print("📚  Bologna Ders Verilerini Yükleme")
    print("=" * 60)

    if flush:
        deleted_count, _ = Course.objects.all().delete()
        print(f"  🗑  Mevcut kurslar silindi: {deleted_count}")

    data = _load_json('bologna_data.json')
    if data is None:
        return


    DEPARTMENT_FACULTY_MAP = {
        'Bilgisayar Mühendisliği': 'Mühendislik ve Doğa Bilimleri Fakültesi',
        'Biyomedikal Mühendisliği': 'Mühendislik ve Doğa Bilimleri Fakültesi',
        'Endüstri Mühendisliği': 'Mühendislik ve Doğa Bilimleri Fakültesi',
    }

    added = 0
    skipped = 0

    for item in data:
        dept_name = item.get('department', 'Genel')
        faculty_name = DEPARTMENT_FACULTY_MAP.get(dept_name, 'Genel Fakülte')

        faculty, _ = Faculty.objects.get_or_create(name=faculty_name)
        department, _ = Department.objects.get_or_create(
            name=dept_name,
            faculty=faculty
        )

        course, created = Course.objects.get_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'ects': int(item['ects']),
                'department': department,
            }
        )

        if created:
            print(f"  ✅  Eklendi: {course.code} - {course.name}")
            added += 1
        else:
            skipped += 1

    print(f"\n  📊  Sonuç: {added} yeni ders eklendi, {skipped} zaten mevcuttu.")


def seed_university_info(flush=False):
    
    print("\n" + "=" * 60)
    print("🏫  Üniversite Genel Bilgilerini Yükleme")
    print("=" * 60)

    if flush:
        deleted_count, _ = UniversityInfo.objects.all().delete()
        print(f"  🗑  Mevcut üniversite bilgileri silindi: {deleted_count}")

    data = _load_json('acibadem_data.json')
    if data is None:
        return

    added = 0
    skipped = 0

    homepage_titles = data.get('homepage_titles', [])
    for i, title in enumerate(homepage_titles, 1):
        _, created = UniversityInfo.objects.get_or_create(
            category='navigation',
            key=f'menu_item_{i}',
            defaults={'value': title}
        )
        if created:
            print(f"  ✅  Navigasyon eklendi: {title}")
            added += 1
        else:
            skipped += 1

    contact_info = data.get('contact_info', {})
    for key, value in contact_info.items():
        _, created = UniversityInfo.objects.get_or_create(
            category='contact',
            key=key,
            defaults={'value': value}
        )
        if created:
            print(f"  ✅  İletişim eklendi: {key} = {value}")
            added += 1
        else:
            skipped += 1

    faculties = data.get('faculties', [])
    for i, fac in enumerate(faculties, 1):
        fac_value = fac if isinstance(fac, str) else json.dumps(fac, ensure_ascii=False)
        _, created = UniversityInfo.objects.get_or_create(
            category='general',
            key=f'faculty_{i}',
            defaults={'value': fac_value}
        )
        if created:
            print(f"  ✅  Fakülte eklendi: {fac_value}")
            added += 1
        else:
            skipped += 1

    if not faculties:
        print("  ℹ  Fakülte verisi henüz mevcut değil (boş liste).")

    print(f"\n  📊  Sonuç: {added} yeni bilgi eklendi, {skipped} zaten mevcuttu.")



def run_seeder(only_courses=False, only_university=False, flush=False):
    print("\n🚀  ACU ChatBot — Data Pipeline başlatılıyor...")

    if not only_university:
        seed_bologna_courses(flush=flush)

    if not only_courses:
        seed_university_info(flush=flush)

    print("\n" + "=" * 60)
    print("✨  Data Pipeline tamamlandı!")
    print("=" * 60 + "\n")



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='ACU ChatBot — Veritabanı seed scripti'
    )
    parser.add_argument(
        '--only-courses', action='store_true',
        help='Sadece Bologna ders verilerini yükle'
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