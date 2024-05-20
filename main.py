import time
import os
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from openpyxl import Workbook

class NewsScraper:
    def __init__(self):
        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)
        self.base_url = "https://www.aljazeera.com/"

    def scrape_news(self, search_phrase, category, num_months):
        try:
            self.driver.get(self.base_url)
            search_field = self.wait.until(EC.presence_of_element_located((By.ID, "search-query")))
            search_field.clear()
            search_field.send_keys(search_phrase)
            search_field.send_keys(Keys.RETURN)

            if category:
                category_link = self.wait.until(EC.presence_of_element_located((By.LINK_TEXT, category)))
                category_link.click()

            #Code to scroll down to load more articles if any are available
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            news_items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "topics-sec-item")))
            excel_file = Workbook()
            sheet = excel_file.active
            sheet.append(["Title", "Date", "Description", "Picture Filename", "Search Phrase Count", "Contains Money"])
            
            for item in news_items:
                title = item.find_element_by_class_name("topics-sec-item-heading").text
                date = item.find_element_by_class_name("topics-sec-item-pubdate").text
                description = item.find_element_by_class_name("topics-sec-item-content").text
                picture_url = item.find_element_by_tag_name("img").get_attribute("src")
                picture_filename = self.download_image(picture_url)

                #Code to count occurrences of search phrase in title and description
                search_phrase_count = title.lower().count(search_phrase.lower()) + description.lower().count(search_phrase.lower())

                #Code to check if title or description contains any amount of money
                contains_money = bool(re.search(r'\$[\d,.]+|[\d,.]+\s?(dollars|USD)', title + " " + description))

                sheet.append([title, date, description, picture_filename, search_phrase_count, contains_money])

            excel_file.save("news_data.xlsx")
            self.driver.quit()
            return True
        except Exception as e:
            print("Error:", e)
            self.driver.quit()
            return False

    def download_image(self, url):
        filename = os.path.basename(url)
        with open(filename, 'wb') as f:
            f.write(requests.get(url).content)
        return filename
