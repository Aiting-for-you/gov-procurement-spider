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
            # --- 提取通用信息 (逻辑同地方公告) ---
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

            # --- 提取主要标的 (智能判断货物类或服务类) ---
            main_info_h = soup.find(lambda tag: tag.name in ['h2', 'strong', 'b'] and '四、主要标的信息' in tag.get_text())
            if main_info_h:
                main_info_table = main_info_h.find_next('table')
                if main_info_table:
                    # 判断表格类型
                    header_text = main_info_table.find('tr').get_text()
                    is_goods_table = '货物' in header_text or '品牌' in header_text

                    first_row = main_info_table.select_one('tr:nth-of-type(2)')
                    if first_row:
                        cols = first_row.find_all('td')
                        item = {}
                        if is_goods_table:
                            # 按货物类解析
                            item = {
                                '名称': cols[2].get_text(strip=True) or 'N/A',
                                '品牌': cols[3].get_text(strip=True) or 'N/A',
                                '规格型号': cols[4].get_text(strip=True) or 'N/A',
                                '数量': cols[5].get_text(strip=True) or 'N/A',
                                '单价': cols[6].get_text(strip=True) or 'N/A',
                            }
                        else:
                            # 按服务类解析
                            item = {
                                '名称': cols[2].get_text(strip=True) or 'N/A', # 服务名称
                                '品牌': 'N/A',
                                '规格型号': 'N/A',
                                '数量': 'N/A',
                                '单价': 'N/A',
                            }
                        final_item = {**general_info, **item}
                        results.append(final_item)
        except Exception as e:
            print(f"解析广东中央公告时出错: {e}")

        if not results:
             results.append({**general_info, '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'})
        return results

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
# if __name__ == '__main__':
#     urls_to_test = {
#         "local": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202502/t20250221_24197324.htm",
#         "central_new": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202505/t20250522_24642661.htm"
#     }
#     for name, url in urls_to_test.items():
#         print(f"\n--- 正在测试: {name} 公告 ---")
#         html_content = get_dynamic_html(url)
#         if html_content:
#             parser = get_parser_for_url(url)
#             if parser:
#                 data = parser.parse(html_content)
#                 print(f"✅ 解析成功，找到 {len(data)} 条记录。")
#                 if len(data) == 1:
#                     print("✅ 规范检查通过：只返回一条记录。")
#                     # 补充采购方式字段，以符合最终规范
#                     data[0]['采购方式'] = 'N/A'
#                     for key, value in data[0].items():
#                         print(f"  {key}: {value}")
#                 else:
#                     print(f"❌ 规范检查失败：返回了 {len(data)} 条记录，应为1条。")
#         print("-" * 30)
