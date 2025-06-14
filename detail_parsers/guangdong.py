# 广东省详情页解析器
# detail_parsers/guangdong.py

from bs4 import BeautifulSoup
from .base import BaseParser

class GuangdongParser(BaseParser):
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
            for tr in soup.select("table tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    k = tds[0].get_text(strip=True)
                    v = tds[1].get_text(strip=True)
                    if "项目编号" in k:
                        result["项目编号"] = v
                    elif "采购方式" in k:
                        result["采购方式"] = v
                    elif "项目名称" in k:
                        result["项目名称"] = v
                    elif "供应商名称" in k:
                        result["供应商名称"] = v
                    elif "中标金额" in k or "成交金额" in k:
                        result["中标金额"] = v
        except:
            pass

        try:
            for table in soup.find_all("table"):
                if "品牌" in table.get_text() and "规格型号" in table.get_text():
                    headers = [th.get_text(strip=True) for th in table.find_all("tr")[0].find_all("td")]
                    items = []
                    for row in table.find_all("tr")[1:]:
                        cols = [td.get_text(strip=True) for td in row.find_all("td")]
                        if len(cols) == len(headers):
                            items.append(dict(zip(headers, cols)))
                    result["主要标的信息"] = str(items)
                    break
        except:
            pass

        return result
