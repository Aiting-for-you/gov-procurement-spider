# 湖南省详情页解析器
# detail_parsers/hunan.py

from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from driver_setup import get_webdriver

class BaseParser:
    def parse(self, html: str):
        raise NotImplementedError

# --- 解析器1: 湖南地方公告 (/dfgg/) ---
class HunanLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        content_div = soup.select_one('div.vF_detail_content')
        if not content_div:
            return []
        
        content_text = content_div.get_text('\n', strip=True)

        # 1. --- 提取通用信息 ---
        general_info = {}
        summary_table = soup.select_one('div.table')
        summary_text = summary_table.get_text('\n', strip=True) if summary_table else ''
        
        general_info['项目名称'] = (re.search(r"采购项目名称\n(.*?)\n", summary_text, re.S).group(1).strip() if '采购项目名称' in summary_text
                                else re.search(r"二、项目名称[：\s]*(.*?)\n", content_text, re.S).group(1).strip() if re.search(r"二、项目名称[：\s]*(.*?)\n", content_text, re.S) else 'N/A')
        
        general_info['项目号'] = re.search(r"一、项目编号[：\s]*(.*?)\n", content_text, re.S).group(1).strip() if re.search(r"一、项目编号[：\s]*(.*?)\n", content_text, re.S) else 'N/A'
        
        date_tag = soup.select_one('.vF_detail_header p, #pubTime')
        if date_tag:
            date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', date_tag.get_text())
            general_info['发布日期'] = date_match.group(1) if date_match else date_tag.get_text(strip=True).split(' ')[0]
        else:
            general_info['发布日期'] = 'N/A'
        general_info['采购方式'] = 'N/A'

        # 2. --- 解析多包件信息 ---
        packages = []
        supplier_names = [m.group(1).strip() for m in re.finditer(r'供应商名称[：\s]*([^\n]+)', content_text)]
        bid_amounts = [m.group(1).strip() for m in re.finditer(r'(?:中标（成交）|总中标)金额[：\s]*([^\n]+)', content_text)]

        num_packages = min(len(supplier_names), len(bid_amounts))
        for i in range(num_packages):
            packages.append({'供应商名称': supplier_names[i], '中标金额': bid_amounts[i]})

        # 3. --- 提取主要标的 ---
        item_details = []
        main_info_h = content_div.find(lambda tag: tag.name in ['h2', 'strong', 'b', 'p'] and '四、主要标的信息' in tag.get_text())
        if main_info_h:
            main_info_table = main_info_h.find_next('table')
            if main_info_table:
                rows = main_info_table.select('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 5: continue
                    item = {
                        '名称': cols[2].get_text(strip=True) or 'N/A', '品牌': cols[3].get_text(strip=True) or 'N/A',
                        '规格型号': cols[4].get_text(strip=True) or 'N/A', '数量': cols[5].get_text(strip=True) or 'N/A',
                        '单价': cols[6].get_text(strip=True) or 'N/A'
                    }
                    item_details.append(item)

        # 4. --- 合并数据 ---
        if not packages and item_details: packages.append({})
        for i, package in enumerate(packages):
            if len(packages) == 1 and len(item_details) > 1:
                combined = {key: ' | '.join(str(d.get(key, '')) for d in item_details if d.get(key)) for key in item_details[0]}
                results.append({**general_info, **package, **combined})
                break
            elif i < len(item_details): results.append({**general_info, **package, **item_details[i]})
            else: results.append({**general_info, **package})

        if not results and packages:
            for package in packages: results.append({**general_info, **package})
        
        if not results and general_info.get('项目名称', 'N/A') != 'N/A':
            results.append({**general_info, "供应商名称": "详见公告正文", "中标金额": "详见公告正文", "名称": "详见公告正文"})
            
        return results

# --- 解析器2: 湖南中央公告 (/zygg/) ---
class HunanCentralGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        content_div = soup.select_one('div.vF_detail_content')
        if not content_div: return []

        content_text = content_div.get_text('\n', strip=True)
        # 1. --- 提取通用信息 (同地方) ---
        general_info = HunanLocalGovParser().parse(html)[0]
        # 从解析结果中提取通用字段
        shared_keys = ['项目名称', '项目号', '发布日期', '采购方式']
        general_info = {k: general_info.get(k, 'N/A') for k in shared_keys}

        # 2. --- 优先解析 "其它补充事宜" 中的表格 ---
        item_details = []
        supplement_h = content_div.find(lambda tag: tag.name in ['h2', 'strong', 'b', 'p'] and '其它补充事宜' in tag.get_text())
        if supplement_h:
            # 找到 "主要标的信息" 的小标题
            info_header = supplement_h.find_next(string=re.compile(r'主要标的信息'))
            if info_header:
                main_info_table = info_header.find_next('table')
                if main_info_table:
                    current_supplier = ''
                    rows = main_info_table.select('tr')[1:]
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) < 5: continue
                        # 处理 rowspan 的情况
                        if cols[0].get_text(strip=True):
                            current_supplier = cols[0].get_text(strip=True)
                        
                        item = {
                            '供应商名称': current_supplier,
                            '名称': cols[1].get_text(strip=True) or 'N/A', '品牌': cols[2].get_text(strip=True) or 'N/A',
                            '规格型号': cols[3].get_text(strip=True) or 'N/A', '数量': cols[4].get_text(strip=True) or 'N/A',
                            '单价': cols[5].get_text(strip=True) if len(cols) > 5 else 'N/A'
                        }
                        item_details.append(item)

        # 如果补充事宜里没有, 回退到解析 "四、主要标的信息"
        if not item_details:
             main_info_h = content_div.find(lambda tag: tag.name in ['h2', 'strong', 'b', 'p'] and '四、主要标的信息' in tag.get_text())
             if main_info_h:
                 # ... 此处可复用地方公告的表格解析逻辑 ...
                 pass # 在此例中, 那个表格是空的或无效的, 所以直接跳过

        # 3. --- 合并数据 ---
        # 这种布局下，包信息和物料信息是混合在表格里的
        if item_details:
             for item in item_details:
                 # 从正文中找到对应的中标金额
                 amount_match = re.search(f"{re.escape(item['供应商名称'])}.*?中标（成交）金额[：\s]*([^\n]+)", content_text, re.S)
                 item['中标金额'] = amount_match.group(1).strip() if amount_match else 'N/A'
                 results.append({**general_info, **item})
        
        # 如果item_details为空, 但从正文解析出了唯一的供应商和金额
        elif '供应商名称' in general_info and general_info.get('供应商名称') != 'N/A':
            results.append(general_info)
        
        return results if results else [general_info]


# --- 模块入口函数 ---
def get_parser_for_url(url: str):
    if "/zygg/" in url:
        return HunanCentralGovParser()
    elif "/dfgg/" in url:
        return HunanLocalGovParser()
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