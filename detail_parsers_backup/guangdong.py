# 广东详情页解析器
# detail_parsers/guangdong.py

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

# --- 解析器1: 广东省地方公告 (/dfgg/) ---
class GuangdongLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        try:
            # --- 提取通用信息 ---
            summary_table = soup.select_one('div.table')
            if summary_table:
                summary_text = summary_table.get_text('\n', strip=True)
                general_info['项目名称'] = re.search(r"采购项目名称\n(.*?)\n", summary_text, re.S).group(1).strip()
                general_info['中标金额'] = re.search(r"总中标金额\n(.*?)\n", summary_text, re.S).group(1).strip()

            content_div = soup.select_one('div.vF_detail_content')
            if content_div:
                content_text = content_div.get_text('\n', strip=True)
                general_info['项目号'] = re.search(r"项目编号[：]\s*(.*?)\n", content_text, re.S).group(1).strip()
                general_info['供应商名称'] = re.search(r"供应商名称[：]\s*(.*?)\n", content_text, re.S).group(1).strip()

            date_tag = soup.select_one('.vF_detail_header p, .table p.tc')
            if date_tag:
                general_info['发布日期'] = re.search(r'(\d{4}年\d{2}月\d{2}日)', date_tag.get_text()).group(1)

            # --- 提取主要标的 ---
            main_info_h = soup.find(lambda tag: tag.name in ['h2', 'strong', 'b'] and '四、主要标的信息' in tag.get_text())
            if main_info_h:
                main_info_table = main_info_h.find_next('table')
                if main_info_table:
                    first_row = main_info_table.select_one('tr:nth-of-type(2)') # 第二行是第一条数据
                    if first_row:
                        cols = first_row.find_all('td')
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
            print(f"解析广东地方公告时出错: {e}")
        
        if not results:
             results.append({**general_info, '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'})
        return results

# --- 解析器2: 广东省中央公告 (/zygg/) ---
class GuangdongCentralGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        try:
            # --- 提取通用信息 (摘要) ---
            summary_table = soup.select_one('div.table')
            if summary_table:
                summary_text = summary_table.get_text('\n', strip=True)
                general_info['项目名称'] = self.search_safe(r"采购项目名称\n(.*?)\n", summary_text)
                general_info['总中标金额'] = self.search_safe(r"总中标金额\n(.*?)\n", summary_text)

            # --- 提取通用信息 (正文) ---
            content_div = soup.select_one('div.vF_detail_content')
            if content_div:
                content_text = content_div.get_text('\n', strip=True)
                general_info['项目号'] = self.search_safe(r"项目编号[：]\s*([^\s（]+)", content_text)

            date_tag = soup.select_one('#pubTime, .vF_detail_header p, .table p.tc')
            if date_tag:
                general_info['发布日期'] = self.search_safe(r'(\d{4}年\d{2}月\d{2}日)', date_tag.get_text())
            
            # --- 提取所有包信息 (供应商、中标金额) ---
            packages = []
            info_heading_tag = soup.find('strong', string=re.compile(r'三、中标（成交）信息'))
            if info_heading_tag:
                current_element = info_heading_tag.find_parent('p')
                current_package = {}
                while current_element := current_element.find_next_sibling():
                    if current_element.find('strong') and '四、主要标的信息' in current_element.get_text():
                        break # Stop at the next section
                    text = current_element.get_text(strip=True)
                    if not text: continue

                    if '供应商名称：' in text:
                        if current_package: packages.append(current_package)
                        current_package = {'供应商名称': text.split('：', 1)[1]}
                    elif '中标（成交）金额：' in text and current_package:
                        current_package['中标金额'] = text.split('：', 1)[1]
                if current_package: packages.append(current_package)

            # --- 提取主要标的信息表 ---
            item_details_map = {}
            main_info_h = soup.find(lambda tag: tag.name in ['h2', 'strong', 'b'] and '四、主要标的信息' in tag.get_text())
            if main_info_h:
                main_info_table = main_info_h.find_next('table')
                if main_info_table:
                    rows = main_info_table.find_all('tr')
                    for row in rows[1:]: # Skip header
                        cols = row.find_all('td')
                        if len(cols) < 7 or not cols[0].get_text(strip=True).isdigit():
                            continue
                        
                        supplier_cell_text = cols[1].get_text(strip=True)
                        package_match = re.search(r'包组?(\d+)', supplier_cell_text)
                        if not package_match: continue
                        
                        package_key = f"包组{package_match.group(1)}"

                        item = {
                            '名称': cols[2].get_text(strip=True) or 'N/A',
                            '品牌': cols[3].get_text(strip=True) or 'N/A',
                            '规格型号': cols[4].get_text(strip=True) or 'N/A',
                            '数量': cols[5].get_text(strip=True) or 'N/A',
                            '单价': cols[6].get_text(strip=True) or 'N/A',
                        }
                        if package_key not in item_details_map:
                            item_details_map[package_key] = []
                        item_details_map[package_key].append(item)

            # --- 合并包和标的信息 ---
            if packages and item_details_map:
                for package in packages:
                    package_name_text = package.get('供应商名称', '')
                    package_match = re.search(r'包组?(\d+)', package_name_text)
                    if not package_match: continue
                    package_key = f"包组{package_match.group(1)}"
                    
                    if package_key in item_details_map:
                        for item in item_details_map[package_key]:
                            results.append({**general_info, **package, **item})
                    else:
                        # 包信息存在，但表格中没有对应的标的信息
                        results.append({**general_info, **package})
            elif packages:
                 # 只有包信息，没有表格信息
                 for package in packages:
                     results.append({**general_info, **package})

        except Exception as e:
            print(f"解析广东中央公告时出错: {e}")

        if not results:
             # Fallback for pages that don't fit the multi-package structure
             final_info = {**general_info}
             final_info.setdefault('供应商名称', 'N/A')
             final_info.setdefault('中标金额', 'N/A')
             results.append({**final_info, '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'})
        return results

    def search_safe(self, pattern, text, group=1):
        match = re.search(pattern, text, re.S)
        return match.group(group).strip() if match else 'N/A'

# --- 模块入口函数 ---
def get_parser_for_url(url: str):
    if "/dfgg/" in url:
        return GuangdongLocalGovParser()
    elif "/zygg/" in url:
        return GuangdongCentralGovParser()
    return None

def get_dynamic_html(url, parser_type='local'):
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
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
        return driver.page_source
    except TimeoutException:
        print(f"页面加载超时: {url}")
        return None
    finally:
        if driver:
            driver.quit()

# # --- 独立测试代码 ---
if __name__ == '__main__':
    urls_to_test = {
        "multi_package_central": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202504/t20250407_24404874.htm",
        "local": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202502/t20250221_24197324.htm",
        "central_new": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202505/t20250522_24642661.htm"
    }
    for name, url in urls_to_test.items():
        print(f"--- 正在测试: {name} 公告 ---")
        html_content = get_dynamic_html(url)
        if html_content:
            parser = get_parser_for_url(url)
            if parser:
                data = parser.parse(html_content)
                print(f"✅ 解析成功，找到 {len(data)} 条记录。")
                for i, record in enumerate(data):
                    print(f"  --- 记录 {i+1} ---")
                    # 补充采购方式字段，以符合最终规范
                    record['采购方式'] = 'N/A'
                    for key, value in record.items():
                        print(f"    {key}: {value}")
                # if len(data) == 1:
                #     print("✅ 规范检查通过：只返回一条记录。")
                #     # 补充采购方式字段，以符合最终规范
                #     data[0]['采购方式'] = 'N/A'
                #     for key, value in data[0].items():
                #         print(f"  {key}: {value}")
                # else:
                #     print(f"❌ 规范检查失败：返回了 {len(data)} 条记录，应为1条。")
        print("-" * 30)
