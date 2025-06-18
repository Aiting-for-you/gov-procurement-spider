# 四川详情页解析器
# detail_parsers/sichuan.py

from bs4 import BeautifulSoup
import re
import sys
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# 确保能找到根目录的模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from driver_setup import get_webdriver

class BaseParser:
    def parse(self, html: str):
        raise NotImplementedError

# --- 四川中央公告解析器 (通用型，自动处理单/多包件) ---
class SichuanCentralGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # --- 提取通用信息 ---
        general_info = {}
        try:
            content_div = soup.select_one('div.vF_detail_content')
            content_text = content_div.get_text('\n', strip=True) if content_div else ''
            
            general_info['项目名称'] = re.search(r'二、项目名称：([^\n]+)', content_text).group(1).strip() if re.search(r'二、项目名称：([^\n]+)', content_text) else 'N/A'
            general_info['项目号'] = re.search(r'一、项目编号：([^\n（]+)', content_text).group(1).strip() if re.search(r'一、项目编号：([^\n（]+)', content_text) else 'N/A'
            general_info['发布日期'] = soup.select_one('#pubTime').get_text(strip=True).split(' ')[0] if soup.select_one('#pubTime') else 'N/A'
            general_info['采购方式'] = 'N/A' # 页面通常不直接提供
        except Exception:
             # 如果基础信息都拿不到，直接返回
            return []

        # --- 提取包信息（供应商、中标金额）---
        packages = []
        try:
            # 多包件逻辑
            if '01包：' in content_text:
                package_sections = re.split(r'(?=\d{2}包：)', content_text)
                for section in package_sections:
                    if '供应商名称：' in section and '中标（成交）金额：' in section:
                        supplier_match = re.search(r'供应商名称：([^\n]+)', section)
                        amount_match = re.search(r'中标（成交）金额：([^\n]+)', section)
                        if supplier_match and amount_match:
                            packages.append({
                                '供应商名称': supplier_match.group(1).strip(),
                                '中标金额': amount_match.group(1).strip()
                            })
            # 单包件逻辑
            else:
                supplier_match = re.search(r'供应商名称：([^\n]+)', content_text)
                amount_match = re.search(r'中标（成交）金额：([^\n]+)', content_text)
                if supplier_match and amount_match:
                    packages.append({
                        '供应商名称': supplier_match.group(1).strip(),
                        '中标金额': amount_match.group(1).strip()
                    })
        except Exception:
            pass # 即使包信息不完整，也继续尝试解析

        # --- 解析主要标的信息表格 ---
        item_details = []
        try:
            main_table = None
            info_header = soup.find('p', string=re.compile(r'四、主要标的信息'))
            if info_header:
                main_table = info_header.find_next('table')

            if main_table:
                rows = main_table.find_all('tr')[1:] # 跳过表头
                for row in rows:
                    cols = row.find_all('td')
                    if not cols or not cols[0].get_text(strip=True): continue
                    
                    item_data = {
                        '名称': cols[2].get_text(strip=True) if len(cols) > 2 else 'N/A',
                        '品牌': cols[3].get_text(strip=True) if len(cols) > 3 else 'N/A',
                        '规格型号': cols[4].get_text(strip=True) if len(cols) > 4 else 'N/A',
                        '数量': cols[5].get_text(strip=True) if len(cols) > 5 else 'N/A',
                        '单价': cols[6].get_text(strip=True) if len(cols) > 6 else 'N/A',
                    }
                    item_details.append(item_data)
        except Exception:
            pass # 表格解析失败也继续

        # --- 合并数据 ---
        if not packages and not item_details:
             return [] # 如果什么都没有，返回空
        
        if not packages and item_details: # 有表格但没提取到包信息
            packages.append({'供应商名称': 'N/A', '中标金额': 'N/A'})

        for i, package in enumerate(packages):
            item_data = item_details[i] if i < len(item_details) else {
                '名称': 'N/A (无物料清单)', '品牌': 'N/A', '规格型号': 'N/A',
                '数量': 'N/A', '单价': 'N/A'
            }
            full_record = {**general_info, **package, **item_data}
            results.append(full_record)
            
        return results

# --- 四川地方公告解析器 ---
class SichuanLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        try:
            header = soup.select_one('div.vF_detail_header')
            project_name = header.select_one('h2').get_text(strip=True) if header else 'N/A'
            pub_date = header.select_one('#pubTime').get_text(strip=True).split(' ')[0] if header and header.select_one('#pubTime') else 'N/A'

            content_div = soup.select_one('div.vF_detail_content')
            content_text = content_div.get_text('\n', strip=True) if content_div else ''
            
            project_number_match = re.search(r'一、项目编号[：:\s]*([^\n（]+)', content_text)
            project_number = project_number_match.group(1).strip() if project_number_match else 'N/A'
            purchase_method = 'N/A'
            
            supplier_name, bid_amount = 'N/A', 'N/A'
            supplier_table = content_div.find(lambda tag: tag.name == 'h4' and '三、采购结果' in tag.text).find_next('table') if content_div.find(lambda tag: tag.name == 'h4' and '三、采购结果' in tag.text) else None
            if supplier_table:
                cols = supplier_table.select('tbody tr td')
                if len(cols) > 2:
                    supplier_name = cols[0].get_text(strip=True)
                    bid_amount = cols[2].get_text(strip=True)
            
            base_info = {
                "发布日期": pub_date, "项目号": project_number, "采购方式": purchase_method,
                "项目名称": project_name, "供应商名称": supplier_name, "中标金额": bid_amount,
            }

            info_table = content_div.find(lambda tag: tag.name == 'h4' and '四、主要标的信息' in tag.text).find_next('table') if content_div.find(lambda tag: tag.name == 'h4' and '四、主要标的信息' in tag.text) else None
            if not info_table:
                results.append({**base_info, "名称": "N/A (工程或服务类)", "品牌": "N/A", "规格型号": "N/A", "数量": "N/A", "单价": "N/A"})
                return results

            rows = info_table.select('tbody tr')
            for row in rows:
                cols = row.select('td')
                if len(cols) < 7: continue

                product_name = cols[2].get_text(strip=True)
                if '空调' not in product_name and '机' not in product_name: continue

                item_data = {
                    "名称": product_name,
                    "品牌": cols[3].get_text(strip=True) or 'N/A',
                    "规格型号": cols[4].get_text(strip=True) or 'N/A',
                    "数量": re.search(r'(\d+\.?\d*)', cols[5].get_text(strip=True)).group(1) if re.search(r'(\d+\.?\d*)', cols[5].get_text(strip=True)) else '0',
                    "单价": re.sub(r'[^\d.]', '', cols[6].get_text(strip=True)) or 'N/A'
                }
                results.append({**base_info, **item_data})
        except Exception as e:
            print(f"解析四川地方公告时出错: {e}")
        
        return results

def get_parser_for_url(url: str):
    if "/zygg/" in url:
        return SichuanCentralGovParser()
    elif "/dfgg/" in url:
        return SichuanLocalGovParser()
    return None

def get_dynamic_html(url: str):
    """
    使用 Selenium 获取指定 url 的动态渲染后的 HTML 内容。
    该函数必须存在于每个省份的解析器模块中，以符合规范。
    """
    driver = None
    try:
        # get_webdriver 函数从项目的根目录的 driver_setup.py 导入
        driver = get_webdriver()
        driver.get(url)
        # 等待页面关键内容加载完成
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.vF_detail_content"))
        )
        return driver.page_source
    except Exception as e:
        print(f"在 get_dynamic_html 中处理页面时出错: {url}, 错误: {e}")
        return None
    finally:
        if driver:
            driver.quit()

# --- get_dynamic_html is now imported from driver_setup --- 