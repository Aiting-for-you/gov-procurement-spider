import pandas as pd
import os
import re
import traceback

def process_file(input_path, logger=None):
    """
    Processes a raw CSV file based on a 'Core Column Alignment' principle.
    - Core columns for alignment: '规格型号', '数量', '单价'
    - A row is split ONLY IF all core columns have the exact same number of items (>1).
    - Other columns ('名称', '品牌') can be broadcast if they have 1 item.
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
        
        log_message(f"▶️ 开始使用[核心列对齐]原则处理文件: {filename}")

        df = pd.read_csv(input_path).fillna('')
        new_rows = []
        delimiter = r'[、；,\n]'

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

            # --- Split all columns into lists of non-empty items ---
            names = [s.strip() for s in re.split(delimiter, name_str) if s.strip()]
            brands = [s.strip() for s in re.split(delimiter, brand_str) if s.strip()]
            specs = [s.strip() for s in re.split(delimiter, spec_str) if s.strip()]
            counts = [s.strip() for s in re.split(delimiter, count_str) if s.strip()]
            prices = [s.strip() for s in re.split(delimiter, price_str) if s.strip()]
            
            # --- Define Core and Non-Core columns for validation ---
            core_lengths = [len(specs), len(counts), len(prices)]
            non_core_lengths = [len(names), len(brands)]
            
            # --- Apply new validation logic ---
            # 1. All core columns must have the same length.
            # 2. That length must be greater than 1 for splitting to be needed.
            is_core_aligned = len(set(core_lengths)) == 1
            num_items = core_lengths[0] if is_core_aligned else 0
            
            # 3. Non-core columns must have length 1 (for broadcasting) or the same length as core columns.
            are_non_core_valid = all(l == 1 or l == num_items for l in non_core_lengths)

            if is_core_aligned and num_items > 1 and are_non_core_valid:
                # --- VALID: Split the row ---
                log_message(f"    - ✅ 第 {index + 2} 行通过核心列对齐校验 ({core_lengths})，拆分为 {num_items} 条记录。")
                for i in range(num_items):
                    new_item = row_dict.copy()
                    new_item['名称'] = names[i if len(names) == num_items else 0]
                    new_item['品牌'] = brands[i if len(brands) == num_items else 0]
                    new_item['规格型号'] = specs[i]
                    new_item['数量'] = counts[i]
                    new_item['单价'] = prices[i]
                    new_item['split_status'] = 'ok'
                    new_rows.append(new_item)
            else:
                # --- INVALID: Do not split ---
                # Check if it was a real mismatch or just a single-item row
                all_lengths = core_lengths + non_core_lengths
                is_single = all(l <= 1 for l in all_lengths)
                if not is_single:
                    log_message(f"    - ⚠️ 第 {index + 2} 行未通过核心列对齐校验 (核心: {core_lengths}, 辅助: {non_core_lengths})，跳过拆分。")
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