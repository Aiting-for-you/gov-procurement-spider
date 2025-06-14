import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import time
import csv

class BaseParser:
    def parse(self, html: str, url: str):
        raise NotImplementedError

# 解析器1：用于解析江苏省自己的域名 (ccgp-jiangsu.gov.cn) 的公告
class JiangsuLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        general_info = {}
        
        # 1. 使用与中央公告一致的、更稳健的方式提取常规信息和发布日期
        try:
            # 发布日期
            title_h2 = soup.select_one('div.vF_detail_header > h2.tc')
            if title_h2:
                p_tag = title_h2.find_next_sibling('p')
                if p_tag:
                    date_span = p_tag.find('span', id='pubTime')
                    if date_span:
                        general_info['发布日期'] = date_span.get_text(strip=True).split(' ')[0]

            # 其他信息从正文提取
            content_div = soup.select_one('.vF_detail_content')
            if content_div:
                # 项目号
                project_num_tag = content_div.find(lambda tag: tag.name in ['h2', 'p'] and '项目编号' in tag.get_text())
                if project_num_tag:
                     general_info['项目号'] = re.sub(r'^\s*一、项目编号[:：\s]*', '', project_num_tag.get_text(strip=True))
                
                # 项目名称
                project_name_tag = content_div.find(lambda tag: tag.name in ['h2', 'p'] and '项目名称' in tag.get_text())
                if project_name_tag:
                    general_info['项目名称'] = re.sub(r'^\s*二、项目名称[:：\s]*', '', project_name_tag.get_text(strip=True))

            # 中标供应商和金额在另一个表格里
            bid_info_title = content_div.find(lambda tag: tag.name in ['h2', 'p'] and '中标（成交）信息' in tag.get_text())
            if bid_info_title:
                bid_table = bid_info_title.find_next('table')
                if bid_table:
                    rows = bid_table.find_all('tr')
                    if len(rows) > 1:
                        cols = rows[1].find_all('td')
                        if len(cols) > 1: general_info['供应商名称'] = cols[1].get_text(strip=True)
                        if len(cols) > 5: general_info['中标金额'] = cols[5].get_text(strip=True)

        except Exception as e:
            print(f"解析地方公告常规信息出错: {e}")
            
        # 2. 精准解析主要标的信息
        results = []
        try:
            main_bid_title = soup.find(lambda tag: tag.name in ['h2', 'p'] and '主要标的信息' in tag.get_text())
            if main_bid_title:
                # 标的信息在一个div里，不是table
                info_div = main_bid_title.find_next('div', {'data-tag-id': '34'})
                if info_div:
                    p_tags = info_div.find_all('p')
                    item_details = {}
                    # 只取第一组信息
                    for p in p_tags:
                        text = p.get_text(strip=True)
                        if '名称：' in text:
                            if '名称' in item_details: break # 开始下一个item了, 结束
                            item_details['名称'] = re.sub(r'^\d+\.\s*名称[:：\s]*', '', text)
                        elif '品牌：' in text and '品牌' not in item_details:
                            item_details['品牌'] = text.replace('品牌：', '').strip()
                        elif '规格型号：' in text and '规格型号' not in item_details:
                            item_details['规格型号'] = text.replace('规格型号：', '').strip()
                        elif '数量：' in text and '数量' not in item_details:
                            item_details['数量'] = text.replace('数量：', '').strip()
                        elif '单价：' in text and '单价' not in item_details:
                            item_details['单价'] = text.replace('单价：', '').strip()
                    
                    if item_details:
                        results.append({**general_info, **item_details})

        except Exception as e:
            print(f"解析地方公告表格信息出错: {e}")

        if not results:
             empty_item = { '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'}
             results.append({**general_info, **empty_item})

        return results

# 解析器2：用于解析在中央域名 (ccgp.gov.cn) 发布的江苏地方公告 (/dfgg/)
class JiangsuCentralLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        general_info = {}

        try:
            # 提取发布日期
            title_h2 = soup.select_one('div.vF_detail_header > h2.tc, h2') # 兼容两种标题位置
            if title_h2:
                date_text_tag = title_h2.find_next_sibling('p')
                if date_text_tag:
                    date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', date_text_tag.get_text())
                    if date_match:
                        general_info['发布日期'] = date_match.group(1)

            # 提取项目编号和名称
            general_info['项目号'] = soup.find(lambda tag: tag.name == 'h2' and '项目编号' in tag.get_text()).get_text(strip=True).replace('一、项目编号：', '')
            general_info['项目名称'] = soup.find(lambda tag: tag.name == 'h2' and '项目名称' in tag.get_text()).get_text(strip=True).replace('二、项目名称：', '')

            # 提取中标信息
            bid_info_table = soup.find(lambda tag: tag.name == 'h2' and '中标（成交）信息' in tag.get_text()).find_next('table')
            if bid_info_table:
                rows = bid_info_table.find_all('tr')
                if len(rows) > 1:
                    cols = rows[1].find_all('td')
                    general_info['供应商名称'] = cols[1].get_text(strip=True)
                    general_info['中标金额'] = cols[5].get_text(strip=True) # 使用元为单位的金额

            # 提取主要标的信息
            main_info_table = soup.find(lambda tag: tag.name == 'h2' and '主要标的信息' in tag.get_text()).find_next('table')
            if main_info_table:
                # 信息被不规范地放在一个单元格里
                cell_text = main_info_table.find_all('tr')[1].find('td').get_text(strip=True)
                item = {
                    '名称': re.search(r'名称：([^品牌]+)', cell_text).group(1).strip() if re.search(r'名称：([^品牌]+)', cell_text) else 'N/A',
                    '品牌': re.search(r'品牌（如有）：([^规]+)', cell_text).group(1).strip() if re.search(r'品牌（如有）：([^规]+)', cell_text) else 'N/A',
                    '规格型号': re.search(r'规格型号：([^数]+)', cell_text).group(1).strip() if re.search(r'规格型号：([^数]+)', cell_text) else 'N/A',
                    '数量': re.search(r'数量：([^单]+)', cell_text).group(1).strip() if re.search(r'数量：([^单]+)', cell_text) else 'N/A',
                    '单价': re.search(r'单价：(.*)', cell_text).group(1).strip() if re.search(r'单价：(.*)', cell_text) else 'N/A',
                }
                results.append({**general_info, **item})

        except Exception as e:
            print(f"解析中央域名下的江苏地方公告时出错: {e}")

        if not results:
            empty_item = { '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A'}
            results.append({**general_info, **empty_item})

        return results

# 解析器3：用于解析在中央域名 (ccgp.gov.cn) 发布的中央公告 (/zygg/)
class JiangsuCentralGovParser(BaseParser):
    def parse(self, html: str):
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
            print(f"解析中央公告常规信息出错: {e}")
            
        results = []
        try:
            bid_title = soup.find(lambda tag: tag.name in ['p', 'strong'] and '主要标的信息' in tag.get_text())
            if bid_title:
                table = bid_title.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    if len(rows) > 1:
                        first_data_row = rows[1]
                        cols = first_data_row.find_all('td')
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
            print(f"解析中央公告表格信息出错: {e}")

        if not results:
            empty_item = { '名称': 'N/A', '品牌': 'N/A', '规格型号': 'N/A', '数量': 'N/A', '单价': 'N/A' }
            results.append({**general_info, **empty_item})
            
        return results

# --- 总入口函数 ---
def get_parser_for_url(url: str):
    """根据URL特征返回最合适的解析器实例"""
    if "ccgp-jiangsu.gov.cn" in url:
        # 江苏省自己的域名，最优先判断
        return JiangsuLocalGovParser()
    elif "/dfgg/" in url:
        # 在中央域名下，但路径是地方公告
        return JiangsuCentralLocalGovParser()
    elif "/zygg/" in url:
        # 在中央域名下，路径是中央公告
        return JiangsuCentralGovParser()
    return None

def get_dynamic_html(url, parser_type='local'): # 签名保持一致
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
        # 等待条件可以根据 parser_type 细化，但当前两个页面结构类似，统一等待body即可
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        # time.sleep(2) # 强制等待可以移除，如果WebDriverWait足够的话
        html = driver.page_source
    except TimeoutException:
        print(f"页面加载超时: {url}")
        html = None
    finally:
        if driver:
            driver.quit()
    return html

def save_to_csv(data, filename):
    if not data:
        print("没有数据可以保存。")
        return
    
    df = pd.DataFrame(data)
    # 按照您的要求，确保测试输出包含所有13个字段
    expected_columns = [
        '发布日期', '项目号', '采购方式', '项目名称', '供应商名称', '中标金额', 
        '名称', '品牌', '规格型号', '数量', '单价', '链接', '省份'
    ]
    for col in expected_columns:
        if col not in df.columns:
            df[col] = 'N/A'
    df = df[expected_columns]
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"数据已成功保存到 {filename}")

if __name__ == '__main__':
    urls = {
        "central": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202506/t20250612_24768548.htm",
        "local": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202506/t20250613_24772760.htm"
    }

    for name, url in urls.items():
        print(f"--- 开始解析 {name} 公告: {url} ---")
        parser_type = 'local' if name == 'local' else 'central'
        html = get_dynamic_html(url, parser_type)
        if html:
            parser = get_parser_for_url(url)
            if parser:
                data = parser.parse(html)
                # 在测试环境下，为数据添加 '链接' 和 '省份' 字段
                for item in data:
                    item['链接'] = url
                    item['省份'] = '江苏'
                save_to_csv(data, f"jiangsu_{name}_details.csv")
        print("--------------------------------------------------")
