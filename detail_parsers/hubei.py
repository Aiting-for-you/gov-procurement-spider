# 湖北省详情页解析器
# detail_parsers/hubei.py

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
        general_info = {}

        try:
            # 修正后的定位逻辑
            # 信息主要在公告概要的表格和正文内容中
            summary_table = soup.select_one('div.table')
            content_div = soup.select_one('div.vF_detail_content')
            
            # 从公告概要表格中提取信息
            if summary_table:
                summary_text = summary_table.get_text('\n', strip=True)
                def find_in_summary(pattern, default='N/A'):
                    match = re.search(pattern, summary_text, re.S)
                    return match.group(1).strip() if match else default
                
                general_info['项目名称'] = find_in_summary(r"采购项目名称\n(.*?)\n")
                general_info['中标金额'] = find_in_summary(r"总中标金额\n(.*?)\n")
            
            # 从正文内容中提取信息
            if content_div:
                content_text = content_div.get_text('\n', strip=True)
                def find_in_content(pattern, default='N/A'):
                    match = re.search(pattern, content_text, re.S)
                    return match.group(1).strip() if match else default

                general_info['项目号'] = find_in_content(r"项目编号[:：]\s*(.*?)\n")
                general_info['供应商名称'] = find_in_content(r"供应商名称[:：]\s*(.*?)\n")

            # 提取发布日期
            date_tag = soup.select_one('.vF_detail_header p, .table p.tc')
            if date_tag:
                date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', date_tag.get_text())
                if date_match:
                    general_info['发布日期'] = date_match.group(1)
            
            # 提取主要标的信息
            main_info_h2 = soup.find(lambda tag: tag.name in ['h2', 'strong', 'b'] and '四、主要标的信息' in tag.get_text())
            if main_info_h2:
                main_info_table = main_info_h2.find_next('table')
                if main_info_table:
                    rows = main_info_table.find_all('tr')
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
                            # 将通用信息和标的信息合并
                            final_item = {**general_info, **item}
                            results.append(final_item)

        except Exception as e:
            print(f"解析湖北地方公告时出错: {e}")

        # 如果没有从表格中解析出具体条目，也要保证返回一条包含通用信息的数据
        if not results:
            # 填充所有在 general_info 中还未找到的字段
            final_item = {
                "发布日期": general_info.get("发布日期", "N/A"),
                "项目号": general_info.get("项目号", "N/A"),
                "项目名称": general_info.get("项目名称", "N/A"),
                "供应商名称": general_info.get("供应商名称", "N/A"),
                "中标金额": general_info.get("中标金额", "N/A"),
                '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'
            }
            results.append(final_item)

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

# The final validation test code has been removed.
