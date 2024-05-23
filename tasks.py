import datetime
import logging
import re
import time
import os
import dateutil.parser
from RPA.Archive import Archive

from RPA.Robocorp.WorkItems import WorkItems
from RPA.HTTP import HTTP
from dateutil.relativedelta import relativedelta
from RPA.Browser.Selenium import Selenium 
from RPA.Excel.Files import Files
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException



logger = logging.getLogger(__name__)
logging.basicConfig(filename='./output/tasks_info.log', level=logging.INFO)
logging.basicConfig(filename='./output/tasks_error.log', level=logging.ERROR)

SITE_URL = "https://www.aljazeera.com/"

possible_amount_formats = [r'\$\d+(\.\d+)?', r'\d+(\.\d+)? dollars', r'\d+(\.\d+)? USD']


class NewsScraperContent:
    def __init__(self, search_input='', month=0):
        self.browser = Selenium()
        self.excel = Files()
        self.title = []
        self.description = []
        self.date = []
        self.picture = []
        self.image_url = []
        self.word_count = []
        self.does_contain_amount = []
        self.search_input = search_input
        self.title_search_phrase_count = 0
        self.description_search_phrase_count = 0
        self.month_range = datetime.datetime.now() - relativedelta(months=month)
        self.is_amount = False

    def open_the_news_website(self):
        """Navigates to the given URL"""
        self.browser.open_available_browser(maximized=False)
        self.browser.go_to(SITE_URL)
        logger.info("Page navigate successfully.")
        self.open_search_field()

    def open_search_field(self):
        """Open and fill the search field"""
        self.browser.element_should_be_visible(locator="class:screen-reader-text", message="Click here to search")
        self.browser.click_button(locator="class:site-header__search-trigger .no-styles-button")
        self.browser.input_text("class:search-bar__input", self.search_input)
        self.browser.element_should_be_visible(locator="class:css-sp7gd", message="Search")
        self.browser.click_button(locator="class:css-sp7gd")
        logger.info("Search goes successfully.")
        self.should_visible_article_list()

    def should_visible_article_list(self):
        """Open latest article"""
        time.sleep(5)
        not_results_found = self.browser.is_element_visible(locator="class:search-results__no-results")
        is_results_visible = self.browser.is_element_visible(locator="class:search-summary__options-title")

        if not_results_found:
            logger.error("Sorry, not results found.")
            self.browser.close_browser()
        elif is_results_visible:
            self.browser.element_should_be_visible(locator="class:search-summary__options-title", message="Sort by")
            logger.info("Articles list display successfully.")
            self.get_article_data()
        else:
            logger.error("Something went wrong.")
            self.browser.close_browser()

    def check_date(self, date):
        if "on" in date.lower():
            date = date.lower().split('on')[-1]
        elif "updated" in date.lower():
            date = date.lower().split('updated')[-1]
        elif "update" in date.lower():
            date = date.lower().split('update')[-1]
        date_time_object = dateutil.parser.parse(date)
        if date_time_object < self.month_range:
            return False
        return True

    def get_article_data(self):
        """Get article data"""
        date = self.browser.find_elements(locator='class:gc__date__date .screen-reader-text')[0].text
        if not self.check_date(date):
            return None
        while True:
            time.sleep(3)
            if self.browser.does_page_contain_element(locator='class:show-more-button'):
                self.browser.execute_javascript("window.scrollTo(0, document.body.scrollHeight);")
                self.browser.find_element(locator='class:show-more-button').click()
                date = self.browser.find_elements(locator='class:gc__date__date .screen-reader-text')[-1].text
                if not self.check_date(date):
                    break
            else:
                break

        articles = self.browser.find_elements(locator="class:u-clickable-card")
        for article in articles:
            article_text = ""
            try:
                title = article.find_element(By.CLASS_NAME, "u-clickable-card__link span").text
                article_text += title
                self.title.append(title)
                is_description = article.find_elements(By.CLASS_NAME, "gc__body-wrap .gc__excerpt p")
                if is_description:
                    article_text += is_description[0].text
                    self.description.append(is_description[0].text)
                    logger.info("Description found")
                else:
                    logger.error("Description not found")
                is_date = article.find_elements(By.CLASS_NAME, "gc__date__date .screen-reader-text")
                if is_date:
                    logger.info(f'Date found')
                    self.date.append(article.find_element(By.CLASS_NAME, "gc__date__date .screen-reader-text").text)
                else:
                    logger.error("Date not found")

                is_image = article.find_elements(By.CLASS_NAME, "gc__image-wrap img")

                if is_image:
                    self.picture.append(is_image[0].get_attribute('alt'))
                    self.image_url.append(is_image[0].get_attribute('src'))
            except StaleElementReferenceException:
                logger.error("Element not found.")
            contain_amount = False
            for pattern in possible_amount_formats:
                if re.search(pattern, article_text):
                    contain_amount = True
                    break
            self.does_contain_amount.append(str(contain_amount))
        self.create_and_save_excel_file()

    def create_and_save_excel_file(self):
        """Create and save excel file"""
        self.excel.create_workbook(path="output/data.xlsx", fmt="xlsx")
        Worksheet_Data = {
            "Title": self.title,
            "Description": self.description,
            "Date": self.date,
            "Picture": self.picture,
            "Title and description search phrase count": self.word_count,
            "Is does contain amount": self.does_contain_amount
        }
        self.excel.append_rows_to_worksheet(Worksheet_Data, header=True)
        self.excel.save_workbook()
        logger.info("Excel file created successfully.")
        self.download_image()

    def download_image(self):
        downloader = HTTP()
        """Download article image with image text"""
        for index, image in enumerate(self.image_url):
            text = self.picture[index]
            downloader.download(image, f'./output/{text[:30]}.jpg')
            logger.info(f"Image downloaded successfully. {image}")


def news_robot_spare_bin_python():
    local_process = os.environ.get("RC_WORKSPACE_ID") is None
    if not local_process:
        work_items = WorkItems()
        work_items.get_input_work_item()
        work_item = work_items.get_work_item_variables()
        variables = work_item.get("variables", dict())
        search_input = variables.get('search_phrase', 'israel war iran')
        months = variables.get('months', 1)
    else:
        search_input = "israel war iran"
        months = 1
    news_content = NewsScraperContent(search_input, months)
    news_content.open_the_news_website()


news_robot_spare_bin_python()