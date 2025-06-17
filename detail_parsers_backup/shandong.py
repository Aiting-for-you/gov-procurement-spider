# 山东省详情页解析器
# detail_parsers/shandong.py

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

# --- 统一的山东公告解析器 (借鉴浙江经验) ---
class ShandongGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        try:
            # --- 提取通用信息 ---
            content_div_text = soup.select_one('div.vF_detail_content').get_text('\n', strip=True) if soup.select_one('div.vF_detail_content') else ''
            
            general_info['项目名称'] = re.search(r"二、项目名称：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['中标金额'] = re.search(r"中标（成交）金额：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['项目号'] = re.search(r"一、项目编号：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['供应商名称'] = re.search(r"三、中标（成交）信息\n供应商名称：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['发布日期'] = re.search(r'(\d{4}年\d{2}月\d{2}日)', soup.select_one('.vF_detail_header p').get_text()).group(1)

            # --- 提取主要标的 (货物类) ---
            main_info_table = soup.select_one('div.vF_detail_content table')
            if main_info_table:
                data_rows = main_info_table.find_all('tr')[1:]
                if data_rows:
                    cols = data_rows[0].find_all('td')
                    if len(cols) > 5:
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
            print(f"解析山东公告时出错: {e}")
        
        if not results:
             results.append({**general_info, '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'})
        return results

# --- 模块入口函数 ---
def get_parser_for_url(url: str):
    # 两个链接都使用同一个解析器
    if "/dfgg/" in url or "/zygg/" in url:
        return ShandongGovParser()
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
#         "local": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202411/t20241126_23718366.htm",
#         "central": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202408/t20240813_22885446.htm"
#     }
#     for name, url in urls_to_test.items():
#         print(f"\n--- 正在测试山东 {name} 公告 ---")
#         html_content = get_dynamic_html(url)
#         if html_content:
#             parser = get_parser_for_url(url)
#             if parser:
#                 data = parser.parse(html_content)
#                 print(f"✅ 解析成功，找到 {len(data)} 条记录。")
#                 if len(data) == 1:
#                     print("✅ 规范检查通过：只返回一条记录。")
#                     data[0]['采购方式'] = 'N/A' # 补充字段
#                     for key, value in data[0].items():
#                         print(f"  {key}: {value}")
#                 else:
#                     print(f"❌ 规范检查失败：返回了 {len(data)} 条记录，应为1条。")
#         print("-" * 30)
