import requests
from bs4 import BeautifulSoup
import re

url = "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

# Find all links that have curUnit and curSunit
links = soup.find_all("a", href=re.compile(r"curUnit=\d+&curSunit=\d+"))
departments = []

for link in links:
    href = link.get("href")
    text = link.get_text(strip=True)
    
    # parse the parameters
    match = re.search(r"curUnit=(\d+)&curSunit=(\d+)", href)
    if match:
        unit = match.group(1)
        sunit = match.group(2)
        departments.append({"faculty_id": int(unit), "department_id": int(sunit), "name": text})

print(f"Found {len(departments)} departments.")
if departments:
    for i in range(min(5, len(departments))):
        print(departments[i])
