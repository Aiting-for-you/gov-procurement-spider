import pandas as pd
import os
import traceback

def process_file(input_path, logger=None):
    """
    Processes a single CSV file to expand rows with multiple items.

    Args:
        input_path (str): The path to the input CSV file.
        logger (object, optional): A logger object with a `put` method. Defaults to None.

    Returns:
        str: Path to the processed file, or None if processing failed.
    """
    def log_message(msg):
        if logger and hasattr(logger, 'put'):
            logger.put(msg)
        else:
            print(msg)

    try:
        if not os.path.exists(input_path):
            log_message(f"❌ 错误：文件不存在 {input_path}")
            return None

        log_message(f"▶️ 开始处理文件: {os.path.basename(input_path)}")
        df = pd.read_csv(input_path)
        
        processed_rows = []
        
        # Define the columns to be split
        # We use a dictionary to map the main column to its potential split-mates
        # This makes the logic more robust if some columns don't need splitting
        columns_to_split = ["名称", "规格型号", "数量", "单价"]
        
        for index, row in df.iterrows():
            # Use the '名称' column as the trigger for splitting
            trigger_column = "名称"
            
            if isinstance(row[trigger_column], str) and '、' in row[trigger_column]:
                # Split all relevant columns by the delimiter '、'
                split_data = {col: str(row[col]).split('、') for col in columns_to_split if col in row and isinstance(row[col], str)}

                # Find the number of items to split into
                num_items = len(split_data.get(trigger_column, []))

                # If for some reason the split results in an empty list, skip
                if num_items == 0:
                    processed_rows.append(row.to_dict())
                    continue
                
                # Verify that all splittable columns have the same number of items
                is_consistent = all(len(items) == num_items for items in split_data.values())
                
                if not is_consistent:
                    log_message(f"    - ⚠️ 警告: 第 {index + 2} 行数据不一致，跳过拆分。各列拆分后的项目数不同。")
                    processed_rows.append(row.to_dict())
                    continue

                log_message(f"    - ℹ️ 正在将第 {index + 2} 行拆分为 {num_items} 条记录...")
                for i in range(num_items):
                    new_row = row.to_dict()
                    for col, items in split_data.items():
                        new_row[col] = items[i].strip()
                    processed_rows.append(new_row)
            else:
                # If no delimiter is found, add the row as is
                processed_rows.append(row.to_dict())

        if not processed_rows:
            log_message("    - 🤷‍♂️ 处理后未生成任何数据。")
            return None

        # Create a new DataFrame from the processed rows
        processed_df = pd.DataFrame(processed_rows)
        
        # Define output path
        directory, filename = os.path.split(input_path)
        name, ext = os.path.splitext(filename)
        output_filename = f"{name}_processed{ext}"
        output_path = os.path.join(directory, output_filename)
        
        # Save the processed DataFrame
        processed_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        log_message(f"✅ 处理完成，文件已保存到: {output_filename}")
        
        return output_path

    except Exception as e:
        log_message(f"❌ 处理文件时发生严重错误: {e}")
        log_message(traceback.format_exc())
        return None

if __name__ == '__main__':
    # Example usage:
    # Create a dummy logger for standalone testing
    class ConsoleLogger:
        def put(self, message):
            print(message)
            
    logger = ConsoleLogger()
    
    # Specify the file to process directly
    # You can change this path to test with other files
    test_file_path = r'output\\四川_空调_2025-05-18_to_2025-05-19.csv'
    
    if os.path.exists(test_file_path):
        process_file(test_file_path, logger=logger)
    else:
        logger.put(f"测试文件不存在: {test_file_path}") 