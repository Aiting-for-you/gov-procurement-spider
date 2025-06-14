# detail_parsers/chongqing.py

from bs4 import BeautifulSoup
from .base import BaseParser
import re
import time
import pandas as pd
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class ChongqingParser(BaseParser):
    def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        result = {
            "发布日期": "",
            "项目号": "",
            "采购方式": "",
            "项目名称": "",
            "供应商名称": "",
            "中标金额": "",
            "名称": "",
            "品牌": "",
            "规格型号": "",
            "数量": "",
            "单价": ""
        }

        # ✅ 发布日期：位于 vF_detail_meta 中
        try:
            meta_div = soup.find("div", class_="vF_detail_meta")
            if meta_div:
                match = re.search(r"发布日期[:：]\s*(\d{4}-\d{2}-\d{2})", meta_div.get_text())
                if match:
                    result["发布日期"] = match.group(1)
        except:
            pass

        # ✅ 字段关键字映射，多关键字增强鲁棒性
        field_map = {
            "项目号": ["项目编号", "项目代码", "采购项目编号"],
            "采购方式": ["采购方式", "招标方式"],
            "项目名称": ["项目名称"],
            "供应商名称": ["中标（成交）供应商名称", "供应商名称", "成交供应商", "中标人"],
            "中标金额": ["中标（成交）金额", "中标金额", "成交金额"]
        }

        # ✅ 提取字段信息：遍历所有表格中的 key-value 行
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                tds = row.find_all(["td", "th"])
                if len(tds) >= 2:
                    key = tds[0].get_text(strip=True)
                    val = tds[1].get_text(strip=True)
                    for field, keywords in field_map.items():
                        if any(k in key for k in keywords) and not result[field]:
                            result[field] = val

        # ✅ 提取主要标的信息表格
        for table in soup.find_all("table"):
            headers = [th.get_text(strip=True) for th in table.find_all("tr")[0].find_all(["td", "th"])]
            header_line = "".join(headers)

            if all(word in header_line for word in ["名称", "品牌", "规格", "数量", "单价"]):
                rows = table.find_all("tr")[1:]
                if not rows:
                    continue
                cols = [td.get_text(strip=True) for td in rows[0].find_all(["td", "th"])]
                header_map = dict(zip(headers, cols))
                for h, v in header_map.items():
                    if "名称" in h:
                        result["名称"] = v
                    elif "品牌" in h:
                        result["品牌"] = v
                    elif "规格" in h or "型号" in h:
                        result["规格型号"] = v
                    elif "数量" in h:
                        result["数量"] = v
                    elif "单价" in h:
                        result["单价"] = v
                break  # 只取第一个匹配的表格

        return result

# ==============================================================================
# Local Government Announcement Parser (地方公告)
# Handles pages with /dfgg/ in URL
# ==============================================================================
class LocalGovParser:
    def find_and_extract(self, soup, label_regex, next_tag='span'):
        """通用函数，用于查找标签并提取其后的文本"""
        try:
            p_element = soup.find(lambda tag: tag.name == 'p' and re.search(label_regex, tag.get_text(strip=True)))
            if p_element and p_element.find(next_tag):
                 return p_element.find(next_tag).get_text(strip=True)
            
            # Fallback for h4 tags
            h4_element = soup.find(lambda tag: tag.name == 'h4' and re.search(label_regex, tag.get_text(strip=True)))
            if h4_element and h4_element.find_next(next_tag):
                 return h4_element.find_next(next_tag).get_text(strip=True)

        except Exception: return "N/A"
        return "N/A"

    def parse_main_bid_table(self, soup):
        """解析主要标的信息表格（地方公告版，不再拆分行）"""
        main_bid_info_list = []
        try:
            main_bid_info_title = soup.find('h4', string=re.compile(r'四、主要标的信息'))
            if not main_bid_info_title: return []

            table_container = main_bid_info_title.find_next('div', class_='panel')
            if not table_container: return []
            
            table = table_container.find('table', class_='table')
            if not table: return []

            rows = table.find_all('tr')
            if len(rows) < 2: return []

            for row in rows[1:]:
                cols = row.find_all('td')
                if not cols or len(cols) < 5: continue
                
                # 直接获取单元格的完整文本，不再拆分
                main_bid_info_list.append({
                    "名称": cols[0].get_text(strip=True),
                    "品牌": cols[1].get_text(strip=True),
                    "规格型号": cols[2].get_text(strip=True),
                    "数量": cols[3].get_text(strip=True),
                    "单价": cols[4].get_text(strip=True),
                })
        except Exception as e:
            print(f"解析地方公告表格时出错: {e}")
        return main_bid_info_list

    def parse(self, html):
        soup = BeautifulSoup(html, 'lxml')
        release_date = soup.find('h3', id='datecandel').get_text(strip=True).replace('发布日期：', '').strip() if soup.find('h3', id='datecandel') else 'N/A'
        project_number = self.find_and_extract(soup, r'一、项目号')
        project_name = self.find_and_extract(soup, r'二、项目名称')
        
        # 最终修正：遍历所有h4标签来查找采购方式，确保能够找到
        procurement_method = "N/A"
        try:
            h4_tags = soup.find_all('h4')
            for tag in h4_tags:
                if '采购方式' in tag.get_text():
                    match = re.search(r'采购方式：(\S+)', tag.get_text())
                    if match:
                        procurement_method = match.group(1).strip()
                        break # 找到后即跳出循环
        except Exception:
             procurement_method = "N/A"

        supplier_name = self.find_and_extract(soup, r'供应商名称')
        bid_amount = self.find_and_extract(soup, r'中标（成交）金额')
        
        main_bid_info = self.parse_main_bid_table(soup)

        final_data = []
        base_info = {
            "发布日期": release_date, "项目号": project_number, "采购方式": procurement_method,
            "项目名称": project_name, "供应商名称": supplier_name, "中标金额": bid_amount,
        }

        if not main_bid_info:
            final_data.append({**base_info, "名称": "N/A", "品牌": "N/A", "规格型号": "N/A", "数量": "N/A", "单价": "N/A"})
        else:
            # 强制只取第一条标的信息，确保一个公告只生成一条数据
            first_item = main_bid_info[0]
            final_data.append({**base_info, **first_item})

        return final_data

# ==============================================================================
# Central Government Announcement Parser (中央公告)
# Handles pages with /zygg/ in URL
# ==============================================================================
class CentralGovParser:
    def parse_complex_table(self, soup):
        data_rows = []
        try:
            table_title = soup.find('strong', string=re.compile(r'四、主要标的信息'))
            if not table_title: return []
            table = table_title.find_next('table')
            if not table: return []
            rows = table.find_all('tr')
            if len(rows) < 2: return []

            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) < 7: continue

                # 直接获取单元格的完整文本，不再拆分
                data_rows.append({
                    "供应商名称": cols[1].get_text(strip=True),
                    "名称": cols[2].get_text(strip=True),
                    "品牌": cols[3].get_text(strip=True),
                    "规格型号": cols[4].get_text(strip=True),
                    "数量": cols[5].get_text(strip=True),
                    "单价": cols[6].get_text(strip=True),
                })
        except Exception as e: print(f"解析中央公告表格时出错: {e}")
        return data_rows

    def parse(self, html):
        soup = BeautifulSoup(html, 'lxml')
        
        # 最终修正：使用更健壮的lambda和正则来提取，并兼容"项目号"和"项目编号"
        project_number = "N/A"
        project_name = "N/A"
        try:
            # 兼容"项目号"和"项目编号"
            num_tag = soup.find(lambda tag: tag.name == 'strong' and '项目' in tag.get_text() and ('号' in tag.get_text() or '编号' in tag.get_text()))
            if num_tag:
                match = re.search(r'(?:项目(?:号|编号))[:：\s]*(\S+)', num_tag.get_text())
                if match:
                    project_number = match.group(1).strip()
                    if '（' in project_number:
                        project_number = project_number.split('（')[0]

            name_tag = soup.find(lambda tag: tag.name == 'strong' and '项目名称' in tag.get_text())
            if name_tag:
                match = re.search(r'项目名称[:：\s]*(.*)', name_tag.get_text())
                if match:
                    project_name = match.group(1).strip()
        except Exception:
            pass # 出错则保持"N/A"

        supplier_info_title = soup.find('strong', string=re.compile(r'三、中标（成交）信息'))
        supplier_name, bid_amount = "N/A", "N/A"
        if supplier_info_title:
            supplier_name_node = supplier_info_title.find_next(string=re.compile(r'供应商名称：'))
            if supplier_name_node: supplier_name = supplier_name_node.replace('供应商名称：', '').strip()
            bid_amount_node = supplier_info_title.find_next(string=re.compile(r'中标（成交）金额：'))
            if bid_amount_node:
                bid_amount = bid_amount_node.replace('中标（成交）金额：', '').strip()
                bid_amount_match = re.search(r'([\d\.]+)', bid_amount)
                if bid_amount_match: bid_amount = bid_amount_match.group(1)
        if project_name == "N/A":
             announcement_title = soup.find('h2', class_='tc')
             if announcement_title: project_name = announcement_title.get_text(strip=True).replace('中标公告','')
        release_date = "N/A"
        pub_time_span = soup.find('span', id='pubTime')
        if pub_time_span:
            full_date_text = pub_time_span.get_text(strip=True)
            # 统一过滤，只保留年月日
            date_match = re.search(r"(\d{4}年\d{2}月\d{2}日)", full_date_text)
            if date_match:
                release_date = date_match.group(1)

        main_bid_info = self.parse_complex_table(soup)

        final_data = []
        item_info = {}

        # 优先使用表格信息，如果表格存在，则只取第一行
        if main_bid_info:
            item_info = main_bid_info[0]
        
        # 如果表格信息为空，则补充默认值
        base_info = {
            "发布日期": release_date,
            "项目号": project_number,
            "采购方式": "N/A",
            "项目名称": project_name,
            "供应商名称": supplier_name,
            "中标金额": bid_amount,
            "名称": item_info.get("名称", "N/A"),
            "品牌": item_info.get("品牌", "N/A"),
            "规格型号": item_info.get("规格型号", "N/A"),
            "数量": item_info.get("数量", "N/A"),
            "单价": item_info.get("单价", "N/A"),
        }

        # 对于中央公告，表格中的供应商名称比页面顶部的更准确
        if "供应商名称" in item_info:
            base_info["供应商名称"] = item_info["供应商名称"]

        final_data.append(base_info)

        return final_data

# ==============================================================================
# Parser Factory and Main Execution Logic
# ==============================================================================
def get_parser_for_url(url):
    """根据URL特征返回合适的解析器实例"""
    if "/cggg/dfgg/" in url:
        print("检测到地方公告，使用 LocalGovParser。")
        return LocalGovParser()
    elif "/cggg/zygg/" in url:
        print("检测到中央公告，使用 CentralGovParser。")
        return CentralGovParser()
    else:
        print(f"警告: 无法为URL确定解析器类型: {url}")
        return None

def get_dynamic_html(url, parser_type='local'):
    """使用Selenium获取动态加载后的HTML"""
    print("使用 Selenium 动态加载页面...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    
    html = ""
    try:
        driver.get(url)
        wait_element_selector = ".vF_detail_content .table tr:nth-child(2)" if parser_type == 'local' else ".vF_detail_content"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_element_selector))
        )
        print("页面动态内容加载完成。")
        html = driver.page_source
    except TimeoutException:
        print("等待动态内容超时，将使用已加载的HTML。")
        html = driver.page_source
    except Exception as e:
        print(f"Selenium加载页面时出错: {e}")
        html = driver.page_source
    finally:
        driver.quit()
    return html
