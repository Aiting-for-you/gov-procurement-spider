# 四川详情页解析器
# detail_parsers/sichuan.py

from bs4 import BeautifulSoup, NavigableString
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

# --- 四川中央公告解析器 (通用型，自动处理单/多包件) ---
class SichuanCentralGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # --- 提取通用信息 ---
        general_info = {}
        content_div = soup.select_one('div.vF_detail_content')
        content_div_text = content_div.get_text('\n', strip=True) if content_div else ''
        
        general_info['项目名称'] = re.search(r'二、项目名称：([^\n]+)', content_div_text).group(1).strip() if re.search(r'二、项目名称：([^\n]+)', content_div_text) else 'N/A'
        general_info['项目号'] = re.search(r'一、项目编号：([^\n（]+)', content_div_text).group(1).strip() if re.search(r'一、项目编号：([^\n（]+)', content_div_text) else 'N/A'
        general_info['发布日期'] = soup.select_one('#pubTime').get_text(strip=True).split(' ')[0] if soup.select_one('#pubTime') else 'N/A'
        
        # --- 智能判断并解析单/多包件信息 ---
        packages = []
        # 检查是否存在多包件的标志
        if '01包：' in content_div_text:
            # 多包件逻辑
            bid_info_paragraphs = soup.select('div.vF_detail_content > p')
            current_package = {}
            for p in bid_info_paragraphs:
                text = p.get_text(strip=True)
                if '供应商名称：' in text:
                    if current_package:
                        packages.append(current_package)
                    current_package = {'供应商名称': text.split('：', 1)[1]}
                elif '中标（成交）金额：' in text and current_package:
                    current_package['中标金额'] = text.split('：', 1)[1]
            if current_package:
                packages.append(current_package)
        else:
            # 单包件逻辑
            supplier_name = re.search(r'供应商名称：([^\n]+)', content_div_text)
            bid_amount = re.search(r'中标（成交）金额：([^\n]+)', content_div_text)
            if supplier_name and bid_amount:
                packages.append({
                    '供应商名称': supplier_name.group(1).strip(),
                    '中标金额': bid_amount.group(1).strip()
                })

        # --- 解析主要标的信息表格 (使用更通用的定位器) ---
        main_table = soup.find('td', string=re.compile(r'\s*货物名称\s*')).find_parent('table')
        if not main_table: # 备用定位器
             main_table = soup.find('p', string=re.compile(r'四、主要标的信息')).find_next('table')

        item_details = []
        if main_table:
            rows = main_table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 1 and "供应商名称" in cols[1].get_text():
                    continue
                if not cols or not cols[0].get_text(strip=True) or (not cols[0].get_text(strip=True).isdigit() and len(packages) > 1):
                     continue # 在多包件情况下，第一列必须是数字

                item_data = {
                    '名称': cols[2].get_text(strip=True) if len(cols) > 2 else 'N/A',
                    '品牌': cols[3].get_text(strip=True) if len(cols) > 3 else 'N/A',
                    '规格型号': cols[4].get_text(strip=True) if len(cols) > 4 else 'N/A',
                    '数量': cols[5].get_text(strip=True) if len(cols) > 5 else 'N/A',
                    '单价': cols[6].get_text(strip=True) if len(cols) > 6 else 'N/A',
                }
                # 对于单包件，它的表格可能没有序号和供应商列
                if len(packages) == 1 and len(cols) < 7:
                     item_data = {
                        '名称': cols[0].get_text(strip=True),
                        '品牌': cols[1].get_text(strip=True),
                        '规格型号': cols[2].get_text(strip=True),
                        '数量': cols[3].get_text(strip=True),
                        '单价': cols[4].get_text(strip=True),
                     }

                item_details.append(item_data)
        
        # --- 合并数据 ---
        if not packages and item_details: # 如果没有从文本中找到包，但找到了表格
            packages.append({})

        for i, package in enumerate(packages):
            # 如果只有一个包，但表格有多行，则全部合并
            if len(packages) == 1 and len(item_details) > 1:
                combined_details = {}
                for key in item_details[0].keys():
                    combined_details[key] = ' | '.join(str(d.get(key, '')) for d in item_details)
                full_item = {**general_info, **package, **combined_details}
                if full_item not in results:
                    results.append(full_item)
            # 标准一对一合并
            elif i < len(item_details):
                full_item = {**general_info, **package, **item_details[i]}
                results.append(full_item)
            # 包信息比表格多
            elif package:
                 results.append({**general_info, **package})


        return results


# --- 四川地方公告解析器 (表格内<br>换行) ---
class SichuanLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        try:
            content_div = soup.select_one('div.vF_detail_content')
            content_div_text = content_div.get_text('\n', strip=True) if content_div else ''

            general_info['项目名称'] = re.search(r'二、项目名称：([^\n]+)', content_div_text).group(1).strip()
            general_info['项目号'] = re.search(r'一、项目编号：([^\s（]+)', content_div_text).group(1).strip()
            general_info['供应商名称'] = re.search(r'供应商名称：([^\n]+)', content_div_text).group(1).strip()
            general_info['中标金额'] = re.search(r'中标（成交）金额：([^\n]+)', content_div_text).group(1).strip()
            general_info['发布日期'] = soup.select_one('#pubTime').get_text(strip=True).split(' ')[0]

            # --- 主要标的信息提取 ---
            item = {}
            main_table = content_div.find('td', string=re.compile(r'^\s*货物名称\s*$')).find_parent('table')
            if main_table:
                data_row = main_table.find_all('tr')[1]
                cols = data_row.find_all('td')
                
                # Helper to parse multi-line cells
                def parse_multiline_cell(cell):
                    return ' | '.join(line.strip().split('：', 1)[-1] for line in cell.get_text(separator='<br>').split('<br>') if line.strip())

                item['名称'] = cols[2].get_text(strip=True)
                item['品牌'] = cols[3].get_text(strip=True)
                item['规格型号'] = parse_multiline_cell(cols[4])
                item['数量'] = parse_multiline_cell(cols[5])
                item['单价'] = parse_multiline_cell(cols[6])
            
            full_item = {**general_info, **item}
            results.append(full_item)
        except Exception as e:
            print(f"解析四川地方公告时出错: {e}")
        return results

def get_parser_for_url(url: str):
    if "/zygg/" in url:
        return SichuanCentralGovParser()
    elif "/dfgg/" in url:
        return SichuanLocalGovParser()
    return None

def get_dynamic_html(url: str) -> str:
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    service = Service(ChromeDriverManager().install())
    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "vF_detail_content"))
        )
        return driver.page_source
    except TimeoutException:
        print(f"页面加载超时: {url}")
        return None
    finally:
        if driver:
            driver.quit()

# # --- 独立测试代码 ---
# if __name__ == '__main__':
#     urls_to_test = {
#         "多包件中央公告": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202505/t20250519_24621154.htm",
#         "单包件中央公告": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202408/t20240822_22963782.htm",
#         "地方公告": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202411/t20241112_23596096.htm"
#     }
#
#     for name, url in urls_to_test.items():
#         print(f"\n--- 正在测试四川{name} ---")
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