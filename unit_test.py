import unittest
from main import NewsScraper
from selenium import webdriver

class TestNewsScraper(unittest.TestCase):
    def test_scrape_news(self):
        scraper = NewsScraper()
        success = scraper.scrape_news("Gaza", "War", 2)
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
