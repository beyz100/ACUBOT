from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import re

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac")
time.sleep(5)

links = driver.find_elements(By.TAG_NAME, "a")
departments = []
for link in links:
    href = link.get_attribute("href")
    if href and "curUnit=" in href and "curSunit=" in href:
        match = re.search(r"curUnit=(\d+)&curSunit=(\d+)", href)
        if match:
            departments.append({
                "faculty_id": match.group(1),
                "department_id": match.group(2),
                "name": link.text.strip()
            })

print(f"Found {len(departments)} departments with Selenium.")
for d in departments[:10]:
    print(d)

driver.quit()
