import json

data = json.load(open('bologna_data.json'))
cs_courses = [c for c in data if c['department'] == 'Bilgisayar Mühendisliği']

print(f'Total CS courses: {len(cs_courses)}')
print('\nAll CS courses:')
for c in cs_courses:
    print(f"{c['code']}: {c['name']}")

