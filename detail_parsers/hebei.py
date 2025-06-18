# 河北详情页解析器 (复用和微调四川的逻辑)
# detail_parsers/hebei.py

from bs4 import BeautifulSoup, NavigableString
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from driver_setup import get_webdriver

class BaseParser:
    def parse(self, html: str):
        raise NotImplementedError

# --- 复用四川中央公告的通用解析器 ---
class HebeiCentralGovParser(BaseParser):
    def parse(self, html: str):
        # 此处完全复用四川中央公告的逻辑，因为它足够通用
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        general_info = {}
        content_div = soup.select_one('div.vF_detail_content')
        content_div_text = content_div.get_text('\n', strip=True) if content_div else ''
        
        general_info['项目名称'] = re.search(r'二、项目名称：([^\n]+)', content_div_text).group(1).strip() if re.search(r'二、项目名称：([^\n]+)', content_div_text) else 'N/A'
        general_info['项目号'] = re.search(r'一、项目编号：([^\n（]+)', content_div_text).group(1).strip() if re.search(r'一、项目编号：([^\n（]+)', content_div_text) else 'N/A'
        general_info['发布日期'] = soup.select_one('#pubTime').get_text(strip=True).split(' ')[0] if soup.select_one('#pubTime') else 'N/A'
        
        packages = []
        if '01包：' in content_div_text:
            bid_info_paragraphs = soup.select('div.vF_detail_content > p')
            current_package = {}
            for p in bid_info_paragraphs:
                text = p.get_text(strip=True)
                if re.match(r'\d+包：', text):
                    if current_package:
                        packages.append(current_package)
                    current_package = {'供应商名称': text}
                elif '中标（成交）金额：' in text and current_package:
                    current_package['中标金额'] = text.replace('中标（成交）金额：', '').strip()
            if current_package:
                packages.append(current_package)
        else:
            supplier_name = re.search(r'供应商名称：([^\n]+)', content_div_text)
            bid_amount = re.search(r'中标（成交）金额：([^\n]+)', content_div_text)
            if supplier_name and bid_amount:
                packages.append({
                    '供应商名称': supplier_name.group(1).strip(),
                    '中标金额': bid_amount.group(1).strip()
                })

        main_table = soup.find('td', string=re.compile(r'\s*货物名称\s*'))
        if main_table:
            main_table = main_table.find_parent('table')
        if not main_table:
            main_table_header = soup.find(lambda tag: tag.name in ['p', 'strong'] and '主要标的信息' in tag.get_text())
            if main_table_header:
                main_table = main_table_header.find_next('table')

        item_details = []
        if main_table:
            rows = main_table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if not cols or not cols[0].get_text(strip=True):
                    continue
                if "供应商名称" in cols[1].get_text(strip=True) if len(cols) > 1 else False:
                    continue
                if cols[0].get_text(strip=True).isdigit() == False and len(packages) > 1:
                    continue

                item_data = {
                    '名称': cols[2].get_text(strip=True) if len(cols) > 2 else 'N/A',
                    '品牌': cols[3].get_text(strip=True) if len(cols) > 3 else 'N/A',
                    '规格型号': cols[4].get_text(strip=True) if len(cols) > 4 else 'N/A',
                    '数量': cols[5].get_text(strip=True) if len(cols) > 5 else 'N/A',
                    '单价': cols[6].get_text(strip=True) if len(cols) > 6 else 'N/A',
                }
                
                if len(packages) == 1 and len(cols) < 7:
                     item_data = {
                        '名称': cols[0].get_text(strip=True),
                        '品牌': cols[1].get_text(strip=True),
                        '规格型号': cols[2].get_text(strip=True),
                        '数量': cols[3].get_text(strip=True),
                        '单价': cols[4].get_text(strip=True),
                     }
                item_details.append(item_data)
        
        if not packages and item_details:
            packages.append({})

        for i, package in enumerate(packages):
            if len(packages) == 1 and len(item_details) > 1:
                combined_details = {}
                for key in item_details[0].keys():
                    combined_details[key] = ' | '.join(str(d.get(key, '')) for d in item_details)
                full_item = {**general_info, **package, **combined_details}
                if full_item not in results:
                    results.append(full_item)
                break 
            elif i < len(item_details):
                full_item = {**general_info, **package, **item_details[i]}
                results.append(full_item)
            elif package:
                 results.append({**general_info, **package})
        
        return results

# --- 微调四川地方公告的解析器 ---
class HebeiLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        
        content_div = soup.select_one('div.vF_detail_content')
        content_div_text = content_div.get_text('\n', strip=True) if content_div else ''

        general_info['项目名称'] = re.search(r'二、项目名称：([^\n]+)', content_div_text).group(1).strip() if re.search(r'二、项目名称：([^\n]+)', content_div_text) else 'N/A'
        general_info['项目号'] = re.search(r'一、项目编号：([^\n（]+)', content_div_text).group(1).strip() if re.search(r'一、项目编号：([^\n（]+)', content_div_text) else 'N/A'
        general_info['供应商名称'] = re.search(r'供应商名称：([^\n]+)', content_div_text).group(1).strip() if re.search(r'供应商名称：([^\n]+)', content_div_text) else 'N/A'
        general_info['中标金额'] = re.search(r'中标（成交）金额：([^\n]+)', content_div_text).group(1).strip() if re.search(r'中标（成交）金额：([^\n]+)', content_div_text) else 'N/A'
        general_info['发布日期'] = soup.select_one('#pubTime').get_text(strip=True).split(' ')[0] if soup.select_one('#pubTime') else 'N/A'

        item = {}
        main_table_header = soup.find(lambda tag: tag.name in ['p', 'strong'] and '主要标的信息' in tag.get_text())
        if main_table_header:
            main_table = main_table_header.find_next('table')
            if main_table:
                rows = main_table.find_all('tr')
                data_row = rows[1] if len(rows) > 1 else None
                if data_row:
                    cols = data_row.find_all('td')
                    item['名称'] = cols[2].get_text(strip=True) if len(cols) > 2 else 'N/A'
                    
                    # 微调之处：处理顿号分隔符
                    item['品牌'] = ' | '.join(cols[3].get_text(strip=True).split('、')) if len(cols) > 3 else 'N/A'
                    item['规格型号'] = ' | '.join(cols[4].get_text(strip=True).split('、')) if len(cols) > 4 else 'N/A'
                    item['数量'] = ' | '.join(cols[5].get_text(strip=True).split('、')) if len(cols) > 5 else 'N/A'
                    item['单价'] = ' | '.join(cols[6].get_text(strip=True).split('、')) if len(cols) > 6 else 'N/A'
        
        full_item = {**general_info, **item}
        results.append(full_item)
        return results

# --- 统一封装 ---
class HebeiGovParser(BaseParser):
    def __init__(self, url):
        if "/zygg/" in url:
            self.parser = HebeiCentralGovParser()
        elif "/dfgg/" in url:
            self.parser = HebeiLocalGovParser()
        else:
            self.parser = None
            
    def parse(self, html: str):
        return self.parser.parse(html)

def get_parser_for_url(url: str):
    if "/zygg/" in url:
        return HebeiCentralGovParser()
    elif "/dfgg/" in url:
        return HebeiLocalGovParser()
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

# # --- 独立测试代码 ---
# if __name__ == '__main__':
#     urls_to_test = {
#         "中央公告": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202407/t20240705_22553840.htm",
#         "地方公告": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202408/t20240809_22853440.htm"
#     }
#
#     for name, url in urls_to_test.items():
#         print(f"\n--- 正在测试河北{name} ---")
#         html_content = get_dynamic_html(url)
#         if html_content:
#             parser = get_parser_for_url(url)
#             if parser:
#                 data = parser.parse(html_content)
#                 print(f"✅ 解析成功，找到 {len(data)} 条记录。")
#                 for i, record in enumerate(data):
#                     print(f"\n--- 记录 {i+1} ---")
#                     record['采购方式'] = 'N/A' # 补充字段
#                     for key, value in record.items():
#                         print(f"  {key}: {value}")
#         print("-" * 30) 