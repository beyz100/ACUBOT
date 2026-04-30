from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac")
time.sleep(3)

try:
    # Let's dump all select elements and their IDs
    selects = driver.find_elements(By.TAG_NAME, "select")
    for s in selects:
        print(f"Select ID: {s.get_attribute('id')}, Name: {s.get_attribute('name')}")
        for opt in s.find_elements(By.TAG_NAME, "option"):
            print(f"  Option: {opt.get_attribute('value')} - {opt.text}")

except Exception as e:
    print(f"Error: {e}")

driver.quit()
