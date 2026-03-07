from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

def scrape_bologna_data():
    course_list = [] 
    options = webdriver.ChromeOptions()
<<<<<<< HEAD
    # options.add_argument('--headless') 
    
    # WebDriver'ı başlat
=======
>>>>>>> 50d014804f8b02560188f1ec002be336c37cad98
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    url = "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246#"
    
    print(f"Loading page: {url}")
    driver.get(url)
    
    try:
<<<<<<< HEAD
        course_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        for row in course_rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) > 2:
                course_code = cells[0].text.strip()
                course_name = cells[1].text.strip()
                course_ects = cells[2].text.strip()
=======
        time.sleep(8) 

        try:
            courses_tab = driver.find_element(By.XPATH, "//span[contains(text(), 'Dersler')] | //*[contains(text(), 'Dersler')]")
            driver.execute_script("arguments[0].click();", courses_tab)
            print("Courses tab clicked.")
            time.sleep(10) 
        except Exception as e:
            print(f"Click action skipped: {e}")

        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Searching across {len(iframes)} iframes...")

        for index in range(len(iframes)):
            driver.switch_to.default_content() 
            driver.switch_to.frame(index)      
            
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.borderColorLisghtGray")
            
            if len(rows) > 0:
                print(f"Found {len(rows)} rows in iframe {index}. Processing...")
>>>>>>> 50d014804f8b02560188f1ec002be336c37cad98
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) >= 6:
                        code = cells[1].text.strip()
                        name = cells[2].text.strip()
                        ects = cells[5].text.strip()
                        
                        if code and code != "Ders Kodu":
                            course_list.append({
                                "code": code,
                                "name": name,
                                "ects": ects
                            })
                break
        
        driver.switch_to.default_content()

    except Exception as e:
        print(f"Error during scraping: {e}")
        
    finally:
<<<<<<< HEAD
        driver.quit()
=======
        driver.quit() 
>>>>>>> 50d014804f8b02560188f1ec002be336c37cad98

    with open("bologna_data.json", "w", encoding="utf-8") as f:
        json.dump(course_list, f, ensure_ascii=False, indent=4)
        
    print(f"\nSuccess! {len(course_list)} courses saved to 'bologna_data.json'.")

if __name__ == "__main__":
    scrape_bologna_data()