# 湖北省详情页解析器
# detail_parsers/hubei.py

from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

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
            # 提取发布日期
            date_text_tag = soup.find('p', class_='tc')
            if not date_text_tag:
                 header = soup.select_one('div.vF_detail_header')
                 if header:
                    date_text_tag = header.find_next_sibling('p')

            if date_text_tag:
                date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', date_text_tag.get_text())
                if date_match:
                    general_info['发布日期'] = date_match.group(1)

            # 提取项目编号和名称
            content_div = soup.select_one('.table, .vF_detail_content')
            if content_div:
                general_info['项目号'] = content_div.find(lambda tag: ('一、项目编号' in tag.get_text() or '项目编号：' in tag.get_text())).get_text(strip=True).split('：')[-1]
                general_info['项目名称'] = content_div.find(lambda tag: ('二、项目名称' in tag.get_text() or '项目名称：' in tag.get_text())).get_text(strip=True).split('：')[-1]
                
                # 提取中标信息
                supplier_tag = content_div.find(lambda tag: '供应商名称' in tag.get_text())
                if supplier_tag:
                    general_info['供应商名称'] = supplier_tag.get_text(strip=True).split('：')[-1]

                amount_tag = content_div.find(lambda tag: '中标（成交）金额' in tag.get_text())
                if amount_tag:
                    general_info['中标金额'] = amount_tag.get_text(strip=True).split('：')[-1]
            
            # 提取主要标的信息
            main_info_h2 = soup.find(lambda tag: tag.name in ['h2', 'strong'] and '主要标的信息' in tag.get_text())
            if main_info_h2:
                main_info_table = main_info_h2.find_next('table')
                if main_info_table:
                    rows = main_info_table.find_all('tr')
                    if len(rows) > 1:
                        # 从第二行开始是数据
                        for data_row in rows[1:]:
                            cols = data_row.find_all('td')
                            # 湖北的表格结构更规范
                            if len(cols) > 6:
                                item = {
                                    '名称': cols[2].get_text(strip=True),
                                    '品牌': cols[3].get_text(strip=True),
                                    '规格型号': cols[4].get_text(strip=True),
                                    '数量': cols[5].get_text(strip=True),
                                    '单价': cols[6].get_text(strip=True),
                                }
                                results.append({**general_info, **item})

        except Exception as e:
            print(f"解析湖北地方公告时出错: {e}")

        if not results:
            empty_item = { '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'}
            results.append({**general_info, **empty_item})

        return results

# --- 解析器2: 用于解析在中央域名 (ccgp.gov.cn) 发布的湖北中央公告 (/zygg/) ---
class HubeiCentralGovParser(BaseParser):
    def parse(self, html: str):
        # 经分析，湖北中央公告与江苏中央公告页面结构高度一致，直接复用其逻辑
        soup = BeautifulSoup(html, 'lxml')
        general_info = {}
        try:
            content_div = soup.select_one('.vF_detail_content')
            if content_div:
                content_text = content_div.get_text('\n', strip=True)
                def find_value(pattern):
                    match = re.search(pattern, content_text, re.DOTALL)
                    return match.group(1).strip() if match else 'N/A'

                general_info['项目号'] = find_value(r"项目编号[:：\s]+(.*?)\n")
                general_info['项目名称'] = find_value(r"项目名称[:：\s]+(.*?)\n")
                general_info['供应商名称'] = find_value(r"供应商名称[:：\s]+(.*?)\n")
                general_info['中标金额'] = find_value(r"中标（成交）金额[:：\s]+(.*?)\n")
            
            title_h2 = soup.select_one('div.vF_detail_header > h2.tc')
            if title_h2:
                p_tag = title_h2.find_next_sibling('p')
                if p_tag:
                    date_span = p_tag.find('span', id='pubTime')
                    if date_span:
                        general_info['发布日期'] = date_span.get_text(strip=True).split(' ')[0]
        except Exception as e:
            print(f"解析湖北中央公告常规信息出错: {e}")
            
        results = []
        try:
            bid_title = soup.find(lambda tag: tag.name in ['p', 'strong'] and '主要标的信息' in tag.get_text())
            if bid_title:
                table = bid_title.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    if len(rows) > 1:
                        # 中央公告的表格结构也比较规范
                        for data_row in rows[1:]:
                            cols = data_row.find_all('td')
                            if len(cols) > 6:
                                item = {
                                    '名称': cols[2].get_text(strip=True),
                                    '品牌': cols[3].get_text(strip=True),
                                    '规格型号': cols[4].get_text(strip=True),
                                    '数量': cols[5].get_text(strip=True),
                                    '单价': cols[6].get_text(strip=True),
                                }
                                results.append({**general_info, **item})
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

def get_dynamic_html(url, parser_type='local'):
    """获取动态HTML，此函数为通用模板，无需修改"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        html = driver.page_source
    except TimeoutException:
        print(f"页面加载超时: {url}")
        html = None
    finally:
        if driver:
            driver.quit()
    return html
