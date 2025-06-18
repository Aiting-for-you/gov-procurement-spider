# detail_parsers/chongqing.py

from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from driver_setup import get_webdriver

# 规范：开发者无需修改 BaseParser
class BaseParser:
    def parse(self, html: str):
        raise NotImplementedError

# --- 重庆中央公告解析器 (/zygg/) ---
class ChongqingCentralGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        content_div = soup.select_one('div.vF_detail_content')
        if not content_div:
            return []
        
        content_text = content_div.get_text('\n', strip=True)
        
        item = {
            "发布日期": "N/A", "项目号": "N/A", "采购方式": "N/A", "项目名称": "N/A",
            "供应商名称": "N/A", "中标金额": "N/A", "名称": "N/A", "品牌": "N/A",
            "规格型号": "N/A", "数量": "N/A", "单价": "N/A",
        }

        # 1. 解析基础信息 (参考sichuan.py，使用正则)
        item['发布日期'] = soup.select_one('#pubTime').get_text(strip=True).split(' ')[0] if soup.select_one('#pubTime') else 'N/A'
        
        project_name_match = re.search(r'二、项目名称[：:\s]*([^\n]+)', content_text)
        if project_name_match:
            item['项目名称'] = project_name_match.group(1).strip()
        else: # 备用方案：直接取标题
            title_tag = soup.select_one('h2.tc')
            if title_tag:
                item['项目名称'] = title_tag.get_text(strip=True).replace('中标公告', '').replace('（成交）结果', '')

        project_num_match = re.search(r'一、项目编号[：:\s]*([^\n（]+)', content_text)
        if project_num_match:
            item['项目号'] = project_num_match.group(1).strip()

        supplier_match = re.search(r'供应商名称[：:\s]*([^\n]+)', content_text)
        if supplier_match:
            item['供应商名称'] = supplier_match.group(1).strip()

        amount_match = re.search(r'中标（成交）金额[：:\s]*([\d,.]+\s*（\s*(?:元|万元)\s*）)', content_text)
        if amount_match:
            item['中标金额'] = amount_match.group(1).strip()

        # 2. 解析主要标的信息表格 (只取第一条有效记录)
        table_title = content_div.find('strong', string=re.compile(r'四、主要标的信息'))
        if not table_title:
             table_title = content_div.find('p', string=re.compile(r'四、主要标的信息'))
        
        if table_title:
            table = table_title.find_next('table')
            if table:
                rows = table.select('tr')
                if len(rows) > 1:
                    # 寻找第一行有效数据行
                    for row in rows[1:]:
                        cols = row.select('td')
                        if len(cols) >= 7 and cols[0].get_text(strip=True): # 确保是数据行
                            # 多行内容处理
                            def get_cell_text(cell_index):
                                cell = cols[cell_index]
                                # 使用<br>分割，然后取每个部分的冒号后的内容
                                parts = [part.split('：', 1)[-1].strip() for part in cell.stripped_strings]
                                return '；'.join(parts) if parts else 'N/A'

                            item["名称"] = get_cell_text(2)
                            item["品牌"] = get_cell_text(3)
                            item["规格型号"] = get_cell_text(4)
                            item["数量"] = get_cell_text(5)
                            item["单价"] = get_cell_text(6)
                            break # 只取第一条

        if item["项目名称"] == "N/A" and item["供应商名称"] == "N/A":
            return []
            
        return [item]

# --- 重庆地方公告解析器 (/dfgg/) ---
class ChongqingLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        content_div = soup.select_one('div.vF_detail_content')
        if not content_div:
            return []
            
        # 采用更健壮的方式：获取全部文本后使用正则解析
        content_text = content_div.get_text('\n', strip=True)

        item = {
            "发布日期": "N/A", "项目号": "N/A", "采购方式": "N/A", "项目名称": "N/A",
            "供应商名称": "N/A", "中标金额": "N/A", "名称": "N/A", "品牌": "N/A",
            "规格型号": "N/A", "数量": "N/A", "单价": "N/A",
        }

        # 1. 解析基础信息 (使用 re.search 提高稳定性)
        item['发布日期'] = content_div.find('h3', id='datecandel').get_text(strip=True).replace('发布日期：', '') if content_div.find('h3', id='datecandel') else 'N/A'
        
        # 项目号
        project_num_match = re.search(r'一、项目号[：\s]*([^\s]+)', content_text)
        if project_num_match:
            item['项目号'] = project_num_match.group(1)

        # 项目名称
        project_name_match = re.search(r'二、项目名称[：\s]*([^\n]+)', content_text)
        if project_name_match:
            item['项目名称'] = project_name_match.group(1).strip()
        
        # 采购方式
        proc_method_match = re.search(r'采购方式[：\s]*([^\s\n]+)', content_text)
        if proc_method_match:
            item['采购方式'] = proc_method_match.group(1).strip()

        # 供应商名称
        supplier_match = re.search(r'供应商名称[：\s]*([^\n]+)', content_text)
        if supplier_match:
            item['供应商名称'] = supplier_match.group(1).strip()
            
        # 中标金额
        amount_match = re.search(r'中标（成交）金额[：\s]*([\d,.]+\s*(?:元|万元))', content_text)
        if amount_match:
            item['中标金额'] = amount_match.group(1).strip()

        # 2. 解析主要标的信息表格 (逻辑保持不变)
        table_title = content_div.find('h4', string=re.compile(r'四、主要标的信息'))
        if table_title:
            table = table_title.find_next('table', class_='table')
            if table:
                rows = table.select('tr')
                if len(rows) > 1:
                    cols = rows[1].find_all('td')
                    if len(cols) >= 5:
                        item["名称"] = cols[0].get_text(strip=True)
                        item["品牌"] = cols[1].get_text(strip=True)
                        item["规格型号"] = cols[2].get_text(strip=True)
                        item["数量"] = cols[3].get_text(strip=True)
                        item["单价"] = cols[4].get_text(strip=True)

        if item["项目名称"] == "N/A" and item["供应商名称"] == "N/A":
            return []
        
        return [item]

# --- 模块必要函数 (根据规范实现) ---
def get_parser_for_url(url: str):
    """根据URL特征返回最合适的解析器实例"""
    if "/dfgg/" in url:
        return ChongqingLocalGovParser()
    elif "/zygg/" in url:
        return ChongqingCentralGovParser()
    # 规范：如果所有情况都不匹配，返回None
    return None

def get_dynamic_html(url, parser_type='local'):
    """
    获取动态HTML，函数签名和基础逻辑保持不变。
    parser_type 在此模块中未使用，但为兼容主程序而保留。
    """
    driver = None
    try:
        driver = get_webdriver()
        driver.get(url)
        # 等待页面主要内容区域加载完成
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.vF_detail_content"))
        )
        html = driver.page_source
    except (TimeoutException, WebDriverException, FileNotFoundError) as e:
        print(f"处理页面时出错: {url}, 错误: {e}")
        html = None # 出错返回 None
    finally:
        if driver:
            driver.quit()
    return html
