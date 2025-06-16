import pandas as pd
import os
import glob
import traceback

def run_converter(target_directory, logger=None):
    """
    Converts all CSV files in the specified directory to XLSX format, with logging.

    Args:
        target_directory (str): The path to the directory containing CSV files.
        logger (object, optional): A logger object with a `put` method for logging.
                                   If None, prints to console. Defaults to None.
    
    Returns:
        bool: True if any files were successfully converted, False otherwise.
    """
    def log_message(msg):
        if logger and hasattr(logger, 'put'):
            logger.put(msg)
        else:
            print(msg)

    csv_files = glob.glob(os.path.join(target_directory, '*.csv'))
    
    if not csv_files:
        log_message("ℹ️ 在目标目录中未找到可转换的 .csv 文件。")
        return False

    success_count = 0
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        try:
            log_message(f"  - 正在转换: {filename}...")
            df = pd.read_csv(file_path, encoding='utf-8-sig') # Use utf-8-sig to handle BOM
            xlsx_path = os.path.splitext(file_path)[0] + '.xlsx'
            
            df.to_excel(xlsx_path, index=False, engine='openpyxl')
            
            # Remove the original CSV file after successful conversion
            os.remove(file_path)
            log_message(f"  ✔ 转换成功: {os.path.basename(xlsx_path)}")
            success_count += 1
            
        except Exception as e:
            error_msg = f"  ❌ 转换失败: {filename}\n     原因: {e}\n     详细信息: {traceback.format_exc()}"
            log_message(error_msg)
    
    if success_count > 0:
        log_message(f"✅ 转换完成！共 {success_count} 个文件已成功转换为 XLSX 并移除原文件。")
    else:
        log_message("🤷‍♀️ 本次没有文件被成功转换。")
        
    return success_count > 0

if __name__ == '__main__':
    
    class DummyLogger:
        def put(self, message):
            print(message)
    
    output_dir = 'output'
    
    print(f"--- 开始独立运行转换器 ---")
    print(f"--- 目标目录: '{output_dir}' ---")
    
    if not os.path.exists(output_dir):
        print(f"\n错误: 目标目录 '{output_dir}' 不存在。")
    else:
        run_converter(output_dir, logger=DummyLogger())
        
    print(f"--- 转换任务结束 ---")
