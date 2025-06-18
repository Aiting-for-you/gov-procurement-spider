# 安徽详情页解析器
# detail_parsers/anhui.py

from bs4 import BeautifulSoup, NavigableString
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

# --- 安徽中央公告解析器 (标准货物类) ---
class AnhuiCentralGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        try:
            content_div = soup.select_one('div.vF_detail_content')
            content_div_text = content_div.get_text('\n', strip=True)
            
            general_info['项目名称'] = re.search(r"二、项目名称：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['中标金额'] = re.search(r"中标（成交）金额：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['项目号'] = re.search(r"一、项目编号：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['供应商名称'] = re.search(r"三、中标（成交）信息\n供应商名称：(.*?)\n", content_div_text, re.S).group(1).strip()
            general_info['发布日期'] = re.search(r'(\d{4}年\d{2}月\d{2}日)', soup.select_one('.vF_detail_header p').get_text()).group(1)

            main_info_table = content_div.select_one('table')
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
                        results.append({**general_info, **item})
        except Exception as e:
            print(f"解析安徽中央公告时出错: {e}")
        
        if not results:
             results.append({**general_info, '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'})
        return results

# --- 安徽地方公告解析器 (特殊非表格布局) ---
class AnhuiLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}
        item = {}
        try:
            content_div = soup.select_one('div.vF_detail_content')
            
            # --- 采用更稳健的逐项提取方法 ---
            general_info['项目名称'] = content_div.find(lambda tag: '项目名称：' in tag.get_text()).get_text(strip=True).replace('二、项目名称：', '')
            general_info['项目号'] = content_div.find(lambda tag: '项目编号：' in tag.get_text()).get_text(strip=True).replace('一、项目编号：', '')
            general_info['供应商名称'] = content_div.find(lambda tag: '供应商名称：' in tag.get_text()).get_text(strip=True).replace('供应商名称：', '')
            general_info['中标金额'] = content_div.find(lambda tag: '中标金额：' in tag.get_text()).get_text(strip=True).replace('中标金额：', '')
            general_info['发布日期'] = re.search(r'(\d{4}年\d{2}月\d{2}日)', soup.select_one('.vF_detail_header p').get_text()).group(1)

            # --- 主要标的信息提取逻辑优化 ---
            main_info_container_header = content_div.find('td', string=re.compile(r'\s*货物类\s*'))
            if main_info_container_header:
                main_info_container = main_info_container_header.find_next_sibling('td')
                if main_info_container:
                    # 最终解决方案：直接在DOM树上查找键值对
                    keys_map = {
                        '名称': '名称',
                        '品牌': '品牌',
                        '规格型号': '规格型号',
                        '数量': '数量',
                        '单价': '单价'
                    }
                    for key_text, item_key in keys_map.items():
                        key_tag = main_info_container.find(lambda tag: tag.name in ['font', 'span'] and key_text in tag.get_text())
                        if key_tag:
                            # 值通常在紧邻的下一个font/span标签里
                            value_tag = key_tag.find_next(['font', 'span'])
                            if value_tag:
                                item[item_key] = value_tag.get_text(strip=True)

        except Exception as e:
            print(f"解析安徽地方公告时出错: {e}")

        # 确保所有字段都存在
        final_item = {
            '名称': item.get('名称', 'N/A'),
            '品牌': item.get('品牌', 'N/A'),
            '规格型号': item.get('规格型号', 'N/A'),
            '数量': item.get('数量', 'N/A'),
            '单价': item.get('单价', 'N/A'),
        }
        results.append({**general_info, **final_item})
        return results


# --- 模块入口函数 ---
def get_parser_for_url(url: str):
    if "/zygg/" in url:
        return AnhuiCentralGovParser()
    elif "/dfgg/" in url:
        return AnhuiLocalGovParser()
    return None

def get_dynamic_html(url):
    driver = None
    try:
        driver = get_webdriver()
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
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
#         "中央公告": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202505/t20250526_24658011.htm",
#         "地方公告": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202506/t20250610_24748356.htm"
#     }
#
#     for name, url in urls_to_test.items():
#         print(f"\n--- 正在测试安徽{name} ---")
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