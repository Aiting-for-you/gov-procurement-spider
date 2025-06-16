import pandas as pd
import os
import re
import traceback
from post_processor import process_file

def parse_spec_and_model(name_str, model_str):
    """
    Intelligently parses the spec and model from the source '名称' and '规格型号' columns.
    Returns a tuple (spec, model).
    """
    name_str = str(name_str).strip()
    model_str = str(model_str).strip()

    # Case 1: Model info is in parentheses
    match = re.search(r'(.+?)\s*[（(](.+?)[)）]$', model_str)
    if match:
        spec = match.group(1).strip()
        model = match.group(2).strip()
        return spec, model

    # Case 2: Keyword-based extraction (e.g., "型号：")
    if '型号：' in model_str:
        parts = model_str.split('型号：')
        spec_part = parts[0].replace('规格：', '').strip()
        model_part = parts[1].strip()
        spec = spec_part if spec_part else name_str
        return spec, model_part

    # Case 3: Split descriptive text from alphanumeric model code
    match = re.match(r'([\u4e00-\u9fa5\s\d\.P匹Ww瓦挂柜匹]+)([A-Z_a-z0-9-].*)', model_str)
    if match:
        spec = match.group(1).strip()
        model = match.group(2).strip()
        return spec, model
        
    # Case 4: If model_str itself looks like a model code, use name_str as spec
    if re.search(r'[A-Za-z]', model_str) and re.search(r'\d', model_str) and len(re.findall(r'[\u4e00-\u9fa5]', model_str)) < 3:
        return name_str, model_str

    # Fallback
    if model_str and model_str not in ['N/A', '']:
        return model_str, 'N/A'
        
    return name_str, 'N/A'


def clean_numeric_value(value_str):
    """Cleans a string to extract a numeric value."""
    if pd.isna(value_str) or not isinstance(value_str, str) or value_str.strip() in ['N/A', '']:
        return 'N/A'
    cleaned_str = re.sub(r'[^\d.]', '', str(value_str))
    try:
        val = float(cleaned_str)
        return int(val) if val == int(val) else val
    except (ValueError, TypeError):
        return value_str

def create_formatted_report(input_csv_path, logger=None):
    """
    Reads the raw CSV, gets the processed (split) data, intelligently formats it, 
    and writes to a new final report CSV.
    """
    def log_message(msg):
        if logger and hasattr(logger, 'put'):
            logger.put(msg)
        else:
            print(msg)

    log_message("第一步：调用预处理器拆分行并进行校验...")
    processed_csv_path = process_file(input_csv_path, logger)
    if not processed_csv_path:
        log_message("❌ 预处理（拆分与校验）失败，格式化中止。")
        return None

    try:
        log_message(f"第二步：开始智能格式化文件: {os.path.basename(processed_csv_path)}")
        df = pd.read_csv(processed_csv_path).fillna('')

        formatted_data = []
        for index, row in df.iterrows():
            try:
                remark = '' # Reset remark, can be re-implemented if needed

                spec, model = parse_spec_and_model(row.get('名称'), row.get('规格型号'))
                
                # Unconditionally clean numeric values for all rows
                quantity = clean_numeric_value(row.get('数量'))
                unit_price = clean_numeric_value(row.get('单价'))

                new_row = {
                    '项目名称': row.get('项目名称', 'N/A'),
                    '中标单位': row.get('供应商名称', 'N/A'),
                    '品牌': row.get('品牌', 'N/A'),
                    '规格': spec,
                    '型号': model,
                    '数量(台)': quantity,
                    '中标单价(元)': unit_price,
                    '中标公示日期': row.get('发布日期', 'N/A'),
                    '备注': remark, # This will be empty now
                    '网址': row.get('链接', 'N/A')
                }
                formatted_data.append(new_row)
            except Exception as e:
                log_message(f"❌ 在处理第 {index + 2} 行时发生错误: {e}")
                log_message(f"    - 问题行数据: {row.to_dict()}")
                log_message(traceback.format_exc())

        if not formatted_data:
            log_message("🤷‍♂️ 格式化后没有数据可以写入。")
            return None

        final_columns = ['项目名称', '中标单位', '品牌', '规格', '型号', '数量(台)', '中标单价(元)', '中标公示日期', '备注', '网址']
        df_formatted = pd.DataFrame(formatted_data, columns=final_columns)
        
        directory, filename = os.path.split(input_csv_path)
        name, _ = os.path.splitext(filename)
        output_csv_path = os.path.join(directory, f"{name}_report.csv")

        log_message("第三步：正在生成最终的CSV报告...")
        df_formatted.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        
        log_message(f"✅ CSV报告生成成功！文件保存在: {output_csv_path}")
        return output_csv_path

    except Exception as e:
        log_message(f"❌ 生成CSV报告时发生严重错误: {e}")
        log_message(traceback.format_exc())
        return None

if __name__ == '__main__':
    class ConsoleLogger:
        def put(self, message):
            print(message)
    
    logger = ConsoleLogger()
    test_file_path = r'output\中标公告_空调_江苏_2025-06-11_to_2025-06-12.csv'
    
    if os.path.exists(test_file_path):
        create_formatted_report(test_file_path, logger)
    else:
        logger.put(f"测试文件不存在: {test_file_path}") 