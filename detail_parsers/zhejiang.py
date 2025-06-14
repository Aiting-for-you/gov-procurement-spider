# 浙江省详情页解析器
# detail_parsers/zhejiang.py

from bs4 import BeautifulSoup
from .base import BaseParser

class ZhejiangParser(BaseParser):
    def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        result = {
            "项目编号": "",
            "采购方式": "",
            "项目名称": "",
            "供应商名称": "",
            "中标金额": "",
            "主要标的信息": ""
        }

        try:
            for row in soup.select("table tr"):
                tds = row.find_all("td")
                if len(tds) >= 2:
                    key = tds[0].get_text(strip=True)
                    val = tds[1].get_text(strip=True)
                    if "项目编号" in key:
                        result["项目编号"] = val
                    elif "采购方式" in key:
                        result["采购方式"] = val
                    elif "项目名称" in key:
                        result["项目名称"] = val
                    elif "中标（成交）供应商名称" in key or "供应商名称" in key:
                        result["供应商名称"] = val
                    elif "中标（成交）金额" in key or "中标金额" in key:
                        result["中标金额"] = val
        except:
            pass

        try:
            # 查找包含“品牌”、“数量”的表格
            for t in soup.find_all("table"):
                if "品牌" in t.get_text() and "数量" in t.get_text():
                    lines = []
                    rows = t.find_all("tr")
                    headers = [th.get_text(strip=True) for th in rows[0].find_all(["td", "th"])]
                    for row in rows[1:]:
                        cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                        if len(cols) == len(headers):
                            lines.append(dict(zip(headers, cols)))
                    result["主要标的信息"] = str(lines)
                    break
        except:
            pass

        return result
