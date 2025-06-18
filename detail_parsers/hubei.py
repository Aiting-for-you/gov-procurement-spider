# 湖北省详情页解析器
# detail_parsers/hubei.py

import sys
import os

# Fix for direct script execution: add project root to python path
# This must be at the top of the file, before any local module imports.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from driver_setup import get_webdriver
import pandas as pd

class BaseParser:
    def parse(self, html: str):
        raise NotImplementedError

# --- 解析器1: 用于解析在中央域名 (ccgp.gov.cn) 发布的湖北地方公告 (/dfgg/) ---
class HubeiLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # 1. 定位主内容区域
        content_div = soup.select_one('div.vF_detail_content')
        if not content_div:
            return results

        # 2. 提取通用信息
        content_text = content_div.get_text('\n', strip=True)
        
        def find_general_value(pattern, default='N/A'):
            match = re.search(pattern, content_text, re.S)
            return match.group(1).strip() if match else default

        project_name = find_general_value(r"(?:三、项目名称|采购项目名称)[:：\s]+(.*?)\n")
        project_number = find_general_value(r"(?:一、项目编号|项目编号)[:：\s]+(.*?)\n")
        
        date_tag = soup.select_one('.vF_detail_header p, .table p.tc, #pubTime')
        publish_date = "N/A"
        if date_tag:
            date_text = date_tag.get_text()
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
            if date_match:
                publish_date = date_match.group(1)

        # 3. 定位并处理 "中标（成交）信息"
        bid_info_header = content_div.find(lambda tag: tag.name in ['p', 'strong', 'h4'] and '中标（成交）信息' in tag.get_text())
        if not bid_info_header:
            return []

        # 从中标信息头开始查找所有兄弟节点，处理每一个包
        current_element = bid_info_header.find_next_sibling()
        package_data = []
        while current_element:
            text = current_element.get_text(" ", strip=True)
            if text.startswith('包名称：'):
                package_data.append({'element': current_element, 'content': []})
            elif package_data:
                package_data[-1]['content'].append(str(current_element))
            current_element = current_element.find_next_sibling()
        
        # 4. 遍历提取每个包的信息
        for package in package_data:
            package_html_str = ''.join(package['content'])
            package_soup = BeautifulSoup(package_html_str, 'lxml')
            package_text = package_soup.get_text('\n', strip=True)

            supplier_name = re.search(r"供应商名称[:：\s]+(.*?)\n", package_text)
            amount = re.search(r"中标（成交）金额[:：\s]+([\d\.]+)", package_text)
            
            supplier_name = supplier_name.group(1).strip() if supplier_name else "N/A"
            amount = f"{amount.group(1).strip()}万元" if amount else "N/A"
            
            item_table = package_soup.find('table')
            if item_table:
                # 提取货物信息
                items_text = item_table.get_text('\n', strip=True).split('货物类\n')
                for item_block in items_text:
                    if not item_block.strip(): continue
                    
                    item_info = {
                        '名称': (re.search(r"名称[:：\s]+(.*?)\n", item_block) or re.search(r"^(.*?)\n", item_block)).group(1).strip(),
                        '品牌': (re.search(r"品牌（如有）[:：\s]+(.*?)\n", item_block) or re.search(r"品牌[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                        '规格型号': (re.search(r"规格型号[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                        '数量': (re.search(r"数量[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                        '单价': (re.search(r"单价[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                    }

                    # 组合成最终结果
                    result_item = {
                        "发布日期": publish_date,
                        "项目号": project_number,
                        "项目名称": project_name,
                        "供应商名称": supplier_name,
                        "中标金额": amount,
                        **item_info
                    }
                    results.append(result_item)
            else: # 如果没有货物表格，至少记录包的信息
                result_item = {
                    "发布日期": publish_date,
                    "项目号": project_number,
                    "项目名称": project_name,
                    "供应商名称": supplier_name,
                    "中标金额": amount,
                    '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'
                }
                results.append(result_item)
        
        # 5. Fallback for single-result pages (no packages)
        if not results and bid_info_header:
            # Find the content block after the header
            single_result_html = ''
            el = bid_info_header.find_next_sibling()
            while el:
                # Stop at the next major section
                if el.name in ['p', 'strong', 'h4'] and re.match(r'[五六七八九十]、', el.get_text(strip=True)):
                    break
                single_result_html += str(el)
                el = el.find_next_sibling()
            
            if single_result_html:
                single_soup = BeautifulSoup(single_result_html, 'lxml')
                single_text = single_soup.get_text('\n', strip=True)

                supplier_name = re.search(r"供应商名称[:：\s]+(.*?)\n", single_text)
                amount = re.search(r"中标（成交）金额[:：\s]+([\d\.]+)", single_text)
                
                supplier_name = supplier_name.group(1).strip() if supplier_name else "N/A"
                amount = f"{amount.group(1).strip()}万元" if amount else "N/A"

                item_table = single_soup.find('table')
                if item_table:
                    items_text = item_table.get_text('\n', strip=True).split('货物类\n')
                    for item_block in items_text:
                        if not item_block.strip(): continue
                        
                        item_info = {
                            '名称': (re.search(r"名称[:：\s]+(.*?)\n", item_block) or re.search(r"^(.*?)\n", item_block)).group(1).strip(),
                            '品牌': (re.search(r"品牌（如有）[:：\s]+(.*?)\n", item_block) or re.search(r"品牌[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                            '规格型号': (re.search(r"规格型号[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                            '数量': (re.search(r"数量[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                            '单价': (re.search(r"单价[:：\s]+(.*?)\n", item_block) or type('',(),{'group':lambda *args: 'N/A'})()).group(1).strip(),
                        }
                        result_item = {
                            "发布日期": publish_date, "项目号": project_number, "项目名称": project_name,
                            "供应商名称": supplier_name, "中标金额": amount, **item_info
                        }
                        results.append(result_item)

        return results

# --- 解析器2: 用于解析在中央域名 (ccgp.gov.cn) 发布的湖北中央公告 (/zygg/) ---
class HubeiCentralGovParser(BaseParser):
    def parse(self, html: str):
        # 经分析，湖北中央公告与江苏中央公告页面结构高度一致，直接复用其逻辑
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        try:
            content_div = soup.select_one('.vF_detail_content')
            if content_div:
                content_text = content_div.get_text('\n', strip=True)
                def find_value(pattern, default='N/A'):
                    match = re.search(pattern, content_text, re.DOTALL)
                    return match.group(1).strip() if match else default

                general_info['项目号'] = find_value(r"项目编号[:：\s]+(.*?)\n")
                general_info['项目名称'] = find_value(r"项目名称[:：\s]+(.*?)\n")
                general_info['供应商名称'] = find_value(r"供应商名称[:：\s]+(.*?)\n")
                general_info['中标金额'] = find_value(r"中标（成交）金额[:：\s]+(.*?)\n")
            
            header_div = soup.select_one('div.vF_detail_header')
            if header_div:
                date_tag = header_div.find('span', id='pubTime')
                if date_tag:
                    general_info['发布日期'] = date_tag.get_text(strip=True).split(' ')[0]
                else: # 备用日期提取
                    p_tag = header_div.find_next_sibling('p')
                    if p_tag:
                         date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', p_tag.get_text())
                         if date_match:
                            general_info['发布日期'] = date_match.group(1)

        except Exception as e:
            print(f"解析湖北中央公告常规信息出错: {e}")
            
        try:
            bid_title = soup.find(lambda tag: tag.name in ['p', 'strong'] and '主要标的信息' in tag.get_text())
            if bid_title:
                table = bid_title.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    if len(rows) > 1:
                        # 只取第一条有效数据行
                        first_data_row = rows[1]
                        cols = first_data_row.find_all('td')
                        if len(cols) > 6:
                            item = {
                                '名称': cols[2].get_text(strip=True) or 'N/A',
                                '品牌': cols[3].get_text(strip=True) or 'N/A',
                                '规格型号': cols[4].get_text(strip=True) or 'N/A',
                                '数量': cols[5].get_text(strip=True) or 'N/A',
                                '单价': cols[6].get_text(strip=True) or 'N/A',
                            }
                            final_item = {**general_info, **item}
                            results.append(final_item)
        except Exception as e:
            print(f"解析湖北中央公告表格信息出错: {e}")

        if not results:
            empty_item = { '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A' }
            results.append({**general_info, **empty_item})
            
        return results

# --- 总入口函数 ---
def get_parser_for_url(url: str):
    """根据URL特征返回最合适的解析器实例"""
    if "/dfgg/" in url:
        return HubeiLocalGovParser()
    elif "/zygg/" in url:
        return HubeiCentralGovParser()
    return None

def get_dynamic_html(url):
    driver = None
    try:
        driver = get_webdriver()
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.vF_detail_content"))
        )
        return driver.page_source
    except (TimeoutException, WebDriverException, FileNotFoundError) as e:
        print(f"处理页面时出错: {url}, 错误: {e}")
        return None
    finally:
        if driver:
            driver.quit()

if __name__ == '__main__':
    # This script is designed to be imported as a module, not run directly.
    # The test code has been removed.
    pass
