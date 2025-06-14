# 详情页解析器基类
# detail_parsers/base.py

from abc import ABC, abstractmethod

class BaseParser(ABC):
    @abstractmethod
    def parse(self, html: str) -> dict:
        pass
