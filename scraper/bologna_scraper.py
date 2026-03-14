from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json


def scrape_bologna_data(faculty_id, department_id, department_name, driver):
    course_list = []
    url = f"https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit={faculty_id}&curSunit={department_id}#"

    print(f"\n[{department_name}] Yükleniyor... URL: {url}")
    driver.get(url)

    try:
        time.sleep(5)

        try:
            courses_tab = driver.find_element(
                By.XPATH,
                "//span[contains(text(), 'Dersler')] | //*[contains(text(), 'Dersler')]"
            )
            driver.execute_script("arguments[0].click();", courses_tab)
            time.sleep(5)
        except Exception as e:
            print(f"Sekme tıklama atlandı: {e}")

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for index in range(len(iframes)):
            driver.switch_to.default_content()
            driver.switch_to.frame(index)

            rows = driver.find_elements(By.CSS_SELECTOR, "tr.borderColorLisghtGray")

            if len(rows) > 0:
                print(f"[{department_name}] {len(rows)} ders bulundu. İşleniyor...")

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if len(cells) >= 6:
                        code = cells[1].text.strip()
                        name = cells[2].text.strip()
                        ects = cells[5].text.strip()

                        if code and code != "Ders Kodu":
                            course_list.append({
                                "department": department_name,
                                "code": code,
                                "name": name,
                                "ects": ects
                            })
                break

        driver.switch_to.default_content()

    except Exception as e:
        print(f"Error ({department_name}): {e}")

    return course_list


if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    departments_to_scrape = [
        {"faculty_id": 14, "department_id": 6246, "name": "Bilgisayar Mühendisliği"},
    ]

    all_courses = []

    for dept in departments_to_scrape:
        dept_courses = scrape_bologna_data(
            faculty_id=dept["faculty_id"],
            department_id=dept["department_id"],
            department_name=dept["name"],
            driver=driver
        )
        all_courses.extend(dept_courses)

    driver.quit()

    with open("bologna_data.json", "w", encoding="utf-8") as f:
        json.dump(all_courses, f, ensure_ascii=False, indent=4)

    print(f"Total of {len(all_courses)} courses 'bologna_data.json' saved.")