from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

def scrape_bologna_data():
    course_list = [] 
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    url = "https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246#"
    
    print(f"Loading page: {url}")
    driver.get(url)
    
    try:
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
        driver.quit() 

    with open("bologna_data.json", "w", encoding="utf-8") as f:
        json.dump(course_list, f, ensure_ascii=False, indent=4)
        
    print(f"\nSuccess! {len(course_list)} courses saved to 'bologna_data.json'.")

if __name__ == "__main__":
    scrape_bologna_data()