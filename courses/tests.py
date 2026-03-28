import json
import os
import tempfile
from django.test import TestCase
from courses.models import Faculty, Department, Course, UniversityInfo


class SeedBolognaCourseTest(TestCase):

    def setUp(self):
        self.test_data = [
            {
                "department": "Bilgisayar Mühendisliği",
                "code": "CSE 101",
                "name": "Programlamaya Giriş",
                "ects": "6"
            },
            {
                "department": "Bilgisayar Mühendisliği",
                "code": "CSE 102",
                "name": "Programlama Pratiği",
                "ects": "6"
            },
        ]

        self.tmp_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        )
        json.dump(self.test_data, self.tmp_file)
        self.tmp_file.close()

    def tearDown(self):
        os.unlink(self.tmp_file.name)

    def test_course_creation(self):
        from seed import seed_bologna_courses, _load_json

        faculty = Faculty.objects.create(name="Mühendislik ve Doğa Bilimleri Fakültesi")
        dept = Department.objects.create(name="Bilgisayar Mühendisliği", faculty=faculty)

        for item in self.test_data:
            Course.objects.get_or_create(
                code=item['code'],
                defaults={
                    'name': item['name'],
                    'ects': int(item['ects']),
                    'department': dept,
                }
            )

        self.assertEqual(Course.objects.count(), 2)
        self.assertTrue(Course.objects.filter(code="CSE 101").exists())
        self.assertTrue(Course.objects.filter(code="CSE 102").exists())

    def test_idempotent_creation(self):
        faculty = Faculty.objects.create(name="Test Fakülte")
        dept = Department.objects.create(name="Test Bölüm", faculty=faculty)

        for _ in range(2):
            for item in self.test_data:
                Course.objects.get_or_create(
                    code=item['code'],
                    defaults={
                        'name': item['name'],
                        'ects': int(item['ects']),
                        'department': dept,
                    }
                )

        self.assertEqual(Course.objects.count(), 2)


class SeedUniversityInfoTest(TestCase):

    def test_navigation_items_creation(self):
        titles = ["Üniversite", "Öğrenci", "Akademik"]
        for i, title in enumerate(titles, 1):
            UniversityInfo.objects.get_or_create(
                category='navigation',
                key=f'menu_item_{i}',
                defaults={'value': title}
            )

        self.assertEqual(
            UniversityInfo.objects.filter(category='navigation').count(), 3
        )

    def test_contact_info_creation(self):
        contact = {
            'campus': 'Kerem Aydınlar Kampüsü',
            'address': 'Kayışdağı cad. No:32',
            'phone': '+90 0216 500 44 44',
            'email': 'info@acibadem.edu.tr',
        }
        for key, value in contact.items():
            UniversityInfo.objects.get_or_create(
                category='contact',
                key=key,
                defaults={'value': value}
            )

        self.assertEqual(
            UniversityInfo.objects.filter(category='contact').count(), 4
        )
        self.assertEqual(
            UniversityInfo.objects.get(category='contact', key='campus').value,
            'Kerem Aydınlar Kampüsü'
        )

    def test_idempotent_creation(self):
        for _ in range(2):
            UniversityInfo.objects.get_or_create(
                category='contact',
                key='phone',
                defaults={'value': '+90 0216 500 44 44'}
            )

        self.assertEqual(
            UniversityInfo.objects.filter(category='contact', key='phone').count(), 1
        )


class UniversityInfoModelTest(TestCase):

    def test_str_representation(self):
        info = UniversityInfo.objects.create(
            category='contact',
            key='phone',
            value='+90 0216 500 44 44'
        )
        self.assertIn('İletişim Bilgileri', str(info))
        self.assertIn('phone', str(info))

    def test_unique_together(self):
        UniversityInfo.objects.create(
            category='contact', key='email', value='test@test.com'
        )
        with self.assertRaises(Exception):
            UniversityInfo.objects.create(
                category='contact', key='email', value='other@test.com'
            )
