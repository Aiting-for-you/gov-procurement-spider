# 详情页解析器基类
# detail_parsers/base.py

from abc import ABC, abstractmethod
from typing import List, Dict

class BaseParser(ABC):
    """
    Abstract base class for all province-specific parsers.
    It defines the common interface that main.py will use to interact with each parser.
    """
    def __init__(self, driver, url_builder, logger, province: str, keyword: str, start_date: str, end_date: str):
        """
        Initializes the parser with necessary components from the main script.
        
        Args:
            driver: The Selenium WebDriver instance.
            url_builder: A function to build search URLs.
            logger: A logging function (or a queue's put method).
            province (str): The Chinese name of the province.
            keyword (str): The search keyword.
            start_date (str): The start date for the search (YYYY-MM-DD).
            end_date (str): The end date for the search (YYYY-MM-DD).
        """
        self.driver = driver
        self.url_builder = url_builder
        self.logger = logger
        self.province = province
        self.keyword = keyword
        self.start_date = start_date
        self.end_date = end_date

    @abstractmethod
    def get_and_parse_results(self) -> List[Dict[str, str]]:
        """
        The main method to be implemented by each province's parser.
        This method should handle the entire process of:
        1. Navigating through result pages.
        2. Extracting detail page links.
        3. Visiting each detail page.
        4. Parsing the content of the detail page.
        5. Returning a list of all parsed data.

        Returns:
            A list of dictionaries, where each dictionary represents a parsed item.
        """
        pass
