import os
import django
import json


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


from courses.models import Faculty, Department, Course

def run_seeder():
    print("Starting database seeding procedure...")


    faculty, _ = Faculty.objects.get_or_create(name="Mühendislik Fakültesi")
    department, _ = Department.objects.get_or_create(
        name="Bilgisayar Mühendisliği", 
        faculty=faculty
    )


    file_path = 'bologna_data.json'
    if not os.path.exists(file_path):
        print(f"Error: {file_path} file cannot be found! Please check the directory.")
        return

    with open(file_path, 'r', encoding='utf-8') as file:
        courses_data = json.load(file)


    added_count = 0
    for item in courses_data:
        course, created = Course.objects.get_or_create(
            code=item['code'],
            defaults={
                'name': item['name'],
                'ects': int(item['ects']), 
                'department': department
            }
        )
        

        if created:
            print(f"Added: {course.code} - {course.name}")
            added_count += 1
        else:
            print(f"Already present: {course.code}")

    print(f"\nTransaction successful! {added_count} new courses added to the database.")

if __name__ == '__main__':
    run_seeder()