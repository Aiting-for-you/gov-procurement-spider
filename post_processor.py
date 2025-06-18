import pandas as pd
import os
import re
import traceback

def intelligent_split(text: str, delimiter: str):
    """
    Splits a string by a delimiter and then processes each part to separate 
    a name from a model in parentheses.
    
    Returns a tuple of two lists: (names, models)
    """
    names, models = [], []
    # Don't split if delimiter is not in the string
    if delimiter not in text:
        text_list = [text]
    else:
        text_list = [s.strip() for s in text.split(delimiter)]
        
    for part in text_list:
        match = re.search(r'(.+?)\s*[（(](.+?)[)）]$', part)
        if match:
            names.append(match.group(1).strip())
            models.append(match.group(2).strip())
        else:
            # If no parenthesis, the whole part is the name/spec, and model is N/A
            names.append(part)
            models.append('N/A')
    return names, models

def process_file(input_path, logger=None):
    """
    Processes a raw CSV file using a prioritized delimiter approach.
    It iterates through a list of delimiters. For each row, it uses the first
    delimiter that successfully splits the 'core columns' into an equal number of items.
    """
    def log_message(msg):
        if logger and hasattr(logger, 'put'):
            logger.put(msg)
        else:
            print(msg)

    if not os.path.exists(input_path):
        log_message(f"❌ 文件不存在: {input_path}")
        return None

    try:
        directory, filename = os.path.split(input_path)
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(directory, f"{name}_processed.csv")
        
        log_message(f"▶️ 开始使用[分隔符优先级]原则处理文件: {filename}")

        df = pd.read_csv(input_path).fillna('')
        new_rows = []
        # 分隔符按优先级排序：分号 > 顿号 > 换行符 > 竖线
        prioritized_delimiters = [';', '；', '、', '\n', '|']

        for index, row in df.iterrows():
            row_dict = row.to_dict()
            
            # --- Get string representations of all relevant columns ---
            name_str = str(row_dict.get('名称', '')).strip()
            brand_str = str(row_dict.get('品牌', '')).strip()
            spec_str = str(row_dict.get('规格型号', '')).strip()
            count_str = str(row_dict.get('数量', '')).strip()
            price_str = str(row_dict.get('单价', '')).strip()

            if any('详见附件' in s for s in [name_str, spec_str, count_str, price_str]):
                log_message(f"    - ℹ️  第 {index + 2} 行包含 '详见附件'，跳过拆分。")
                row_dict['split_status'] = 'attachment'
                new_rows.append(row_dict)
                continue

            split_successful = False
            for delim in prioritized_delimiters:
                # --- Attempt to split core columns with the current delimiter ---
                new_names, new_specs = intelligent_split(spec_str, delim)
                counts = [s.strip() for s in count_str.split(delim) if s.strip()]
                prices = [s.strip() for s in price_str.split(delim) if s.strip()]

                core_lengths = [len(new_specs), len(counts), len(prices)]
                
                # --- Check for core alignment ---
                is_core_aligned = all(x == core_lengths[0] for x in core_lengths)
                num_items = core_lengths[0] if is_core_aligned else 0

                if is_core_aligned and num_items > 1:
                    # --- If core is aligned, check non-core columns ---
                    brands = [s.strip() for s in brand_str.split(delim) if s.strip()]
                    non_core_lengths = [len(new_names), len(brands)]
                    
                    are_non_core_valid = all(l == 1 or l == num_items for l in non_core_lengths)

                    if are_non_core_valid:
                        # --- SUCCESS: Split the row and break from the delimiter loop ---
                        log_message(f"    - ✅ 第 {index + 2} 行使用分隔符 '{delim}' 成功匹配，拆分为 {num_items} 条。")
                        for i in range(num_items):
                            new_item = row_dict.copy()
                            new_item['名称'] = new_names[i]
                            new_item['品牌'] = brands[i if len(brands) == num_items else 0]
                            new_item['规格型号'] = new_specs[i]
                            new_item['数量'] = counts[i]
                            new_item['单价'] = prices[i]
                            new_item['split_status'] = 'ok'
                            new_rows.append(new_item)
                        
                        split_successful = True
                        break # Exit the delimiter loop for this row

            if not split_successful:
                # --- Did not split: Append original row ---
                all_lengths = [len(re.split(r'[、；;\n|]', s)) for s in [name_str, brand_str, spec_str, count_str, price_str]]
                is_single = all(l <= 1 for l in all_lengths)
                
                if not is_single:
                    log_message(f"    - ⚠️ 第 {index + 2} 行未使用任何优先分隔符成功匹配，跳过拆分。")
                    row_dict['split_status'] = 'mismatched'
                else:
                    row_dict['split_status'] = 'single_item'
                new_rows.append(row_dict)

        if not new_rows:
            log_message("🤷‍♂️ 文件处理后没有数据。")
            return None

        processed_df = pd.DataFrame(new_rows)
        processed_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        log_message(f"✅ 预处理完成，文件已保存到: {os.path.basename(output_path)}")
        return output_path
    
    except Exception as e:
        log_message(f"❌ 在 process_file 中发生严重错误: {e}")
        log_message(traceback.format_exc())
        return None

if __name__ == '__main__':
    class ConsoleLogger:
        def put(self, message):
            print(message)
    
    logger = ConsoleLogger()
    test_file_path = r'output\中标公告_空调_江苏_2025-06-11_to_2025-06-12.csv'
    
    if os.path.exists(test_file_path):
        process_file(test_file_path, logger)
    else:
        logger.put(f"测试文件不存在: {test_file_path}") 