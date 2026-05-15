import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to sys.path to import the scraper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from indoscraping.scraper.news.cnbcindonesia import get_categories, get_articles_for_category, scrape_article, DEFAULT_TIMEOUT

class TestCNBCTimeout(unittest.TestCase):

    @patch('requests.get')
    def test_get_categories_timeout(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><select onchange="articleKanalHandle(this)"></select></html>'
        mock_get.return_value = mock_response

        # We need to mock BeautifulSoup as well because it's used inside get_categories
        with patch('indoscraping.scraper.news.cnbcindonesia.BeautifulSoup') as mock_bs:
            get_categories()

        # Verify that requests.get was called with the DEFAULT_TIMEOUT
        mock_get.assert_called_with(unittest.mock.ANY, headers=unittest.mock.ANY, timeout=DEFAULT_TIMEOUT)

    @patch('requests.get')
    def test_get_articles_for_category_timeout(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><article><a></a></article></html>'
        mock_response_empty = MagicMock()
        mock_response_empty.status_code = 200
        mock_response_empty.text = '<html></html>'

        mock_get.side_effect = [mock_response, mock_response_empty]

        category = {'name': 'News', 'slug': 'news', 'id': '1'}
        with patch('indoscraping.scraper.news.cnbcindonesia.BeautifulSoup') as mock_bs:
            mock_soup = MagicMock()
            mock_bs.return_value = mock_soup
            mock_soup.select.side_effect = [[MagicMock()], []]
            get_articles_for_category(category, '2023/01/01')

        # Verify that requests.get was called with the DEFAULT_TIMEOUT
        mock_get.assert_called_with(unittest.mock.ANY, headers=unittest.mock.ANY, timeout=DEFAULT_TIMEOUT)

    @patch('requests.get')
    def test_scrape_article_timeout(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><h1>Title</h1></html>'
        mock_get.return_value = mock_response

        with patch('indoscraping.scraper.news.cnbcindonesia.BeautifulSoup') as mock_bs:
            scrape_article('http://example.com/article')

        # Verify that requests.get was called with the DEFAULT_TIMEOUT
        mock_get.assert_called_with('http://example.com/article', headers=unittest.mock.ANY, timeout=DEFAULT_TIMEOUT)

if __name__ == '__main__':
    unittest.main()
