import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkcalendar import Calendar
import threading
import queue
import os
from datetime import datetime
import sys
import subprocess
import logging
import traceback

# Now that logger_config.py is created, we can import from it.
from logger_config import QueueHandler
from main import start_crawl_process
from converter import run_converter
from PIL import Image
# Centralize province data by importing from the new mapping file
from province_mapping import PROVINCE_PINYIN_MAP, get_chinese_province_list


# --- Helper Function for Pathing ---
def get_base_path():
    """ Get the base path for the application, handling frozen (packaged) state. """
    if getattr(sys, 'frozen', False):
        # The application is running as a bundled executable
        return os.path.dirname(sys.executable)
    else:
        # The application is running in a normal Python environment
        return os.path.dirname(os.path.abspath(__file__))

# --- Constants ---
# The single source of truth for provinces is now province_mapping.py
CHINESE_PROVINCES = get_chinese_province_list()
BASE_PATH = get_base_path()
DEFAULT_OUTPUT_DIR = os.path.join(BASE_PATH, "output")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("中国政府采购数据采集器")
        self.geometry("700x650") # Increased height for progress bar

        # --- Frame Setup ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Adjusted row for log frame

        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)

        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.progress_frame = ctk.CTkFrame(self)
        self.progress_frame.grid(row=2, column=0, padx=10, pady=0, sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        # --- Input Widgets ---
        self.province_label = ctk.CTkLabel(self.input_frame, text="省份:")
        self.province_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.province_menu = ctk.CTkOptionMenu(self.input_frame, values=CHINESE_PROVINCES)
        self.province_menu.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        self.keyword_label = ctk.CTkLabel(self.input_frame, text="关键词:")
        self.keyword_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.keyword_entry = ctk.CTkEntry(self.input_frame, placeholder_text="例如: 采购")
        self.keyword_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        today = datetime.now()
        self.start_date_label = ctk.CTkLabel(self.input_frame, text="开始日期:")
        self.start_date_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.start_date_entry = ctk.CTkEntry(self.input_frame, placeholder_text="YYYY-MM-DD")
        self.start_date_entry.grid(row=2, column=1, padx=(10,0), pady=5, sticky="ew")
        self.start_date_entry.insert(0, today.replace(day=1).strftime("%Y-%m-%d"))
        self.start_date_button = ctk.CTkButton(self.input_frame, text="📅", width=30, command=lambda: self.open_calendar(self.start_date_entry))
        self.start_date_button.grid(row=2, column=2, padx=(5,10), pady=5)

        self.end_date_label = ctk.CTkLabel(self.input_frame, text="结束日期:")
        self.end_date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.end_date_entry = ctk.CTkEntry(self.input_frame, placeholder_text="YYYY-MM-DD")
        self.end_date_entry.grid(row=3, column=1, padx=(10,0), pady=5, sticky="ew")
        self.end_date_entry.insert(0, today.strftime("%Y-%m-%d"))
        self.end_date_button = ctk.CTkButton(self.input_frame, text="📅", width=30, command=lambda: self.open_calendar(self.end_date_entry))
        self.end_date_button.grid(row=3, column=2, padx=(5,10), pady=5)
        
        self.output_dir_button = ctk.CTkButton(self.input_frame, text="选择保存目录", command=self.select_output_directory)
        self.output_dir_button.grid(row=4, column=0, padx=10, pady=10, sticky="w")
        
        # Ensure the default output directory exists
        if not os.path.exists(DEFAULT_OUTPUT_DIR):
            os.makedirs(DEFAULT_OUTPUT_DIR)
            
        self.output_dir = DEFAULT_OUTPUT_DIR
        self.output_dir_label = ctk.CTkLabel(self.input_frame, text=f"保存在: {self.output_dir}", wraplength=450, justify="left")
        self.output_dir_label.grid(row=4, column=1, columnspan=2, padx=10, pady=10, sticky="w")

        # --- Action Widgets ---
        self.start_button = ctk.CTkButton(self.action_frame, text="开始爬取", command=self.start_crawling)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.convert_button = ctk.CTkButton(self.action_frame, text="将结果转为Excel", command=self.run_conversion)
        self.convert_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.format_button = ctk.CTkButton(self.action_frame, text="生成规范报告", command=self.start_formatting_thread, state="disabled")
        self.format_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        # --- Progress & Log Widgets ---
        self.progressbar = ctk.CTkProgressBar(self.progress_frame)
        # self.progressbar.grid(row=0, column=0, padx=10, pady=5, sticky="ew") # Initially hidden
        self.progressbar.set(0)

        self.log_textbox = ctk.CTkTextbox(self.log_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, sticky="nsew")
        self.log_textbox.tag_config("info", foreground="cyan")
        self.log_textbox.tag_config("success", foreground="green")
        self.log_textbox.tag_config("error", foreground="red")

        # --- Threading & Logging Setup ---
        self.log_queue = queue.Queue()
        # Create a handler that redirects logs to our queue
        self.queue_handler = QueueHandler(self.log_queue)
        
        # Get the root logger and add our queue handler to it
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.INFO)
        self.root_logger.addHandler(self.queue_handler)

        # Start polling the queue for new log messages
        self.after(100, self.process_log_queue)

        self.last_raw_csv_path = None

    def open_calendar(self, entry_widget):
        cal_win = ctk.CTkToplevel(self)
        cal_win.title("选择日期")
        cal_win.transient(self)
        cal_win.grab_set()

        try:
            current_date = datetime.strptime(entry_widget.get(), "%Y-%m-%d")
        except ValueError:
            current_date = datetime.now()
            
        cal = Calendar(cal_win, selectmode='day',
                       year=current_date.year, month=current_date.month, day=current_date.day,
                       date_pattern='yyyy-mm-dd')
        cal.pack(padx=10, pady=10)

        def on_date_select():
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, cal.get_date())
            cal_win.destroy()

        ctk.CTkButton(cal_win, text="确定", command=on_date_select).pack(pady=10)

    def select_output_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir = directory
            self.output_dir_label.configure(text=f"保存在: {self.output_dir}")

    def process_log_queue(self):
        try:
            while True:
                msg_record = self.log_queue.get_nowait()
                
                # Special message check for crawl completion
                if msg_record == "CRAWL_COMPLETE":
                    self.task_complete()
                    logging.info("✅ 爬取任务完成。")
                    continue
                elif msg_record == "CRAWL_FAILED":
                    self.task_complete(failed=True)
                    logging.error("❌ 爬取任务失败，请检查日志。")
                    continue
                elif isinstance(msg_record, str) and msg_record.startswith("CRAWL_SUCCESS:"):
                    self.last_raw_csv_path = msg_record.split(":", 1)[1].strip()
                    logging.info(f"🎉 爬取成功！原始数据文件：{os.path.basename(self.last_raw_csv_path)}")
                    self.task_complete()
                    self.format_button.configure(state="normal") # Enable formatting
                    continue
                elif msg_record == "FORMAT_COMPLETE":
                    self.task_complete()
                    logging.info("✅ 报告格式化完成。")
                    continue
                elif msg_record == "FORMAT_FAILED":
                    self.task_complete(failed=True)
                    logging.error("❌ 报告格式化失败。")
                    continue

                # For all other log records, just display them
                self.log_textbox.configure(state="normal")
                # Simple logic to apply tags based on log level
                if "ERROR" in msg_record:
                    self.log_textbox.insert(tk.END, msg_record + "\n", "error")
                elif "SUCCESS" in msg_record or "🎉" in msg_record:
                    self.log_textbox.insert(tk.END, msg_record + "\n", "success")
                else:
                    self.log_textbox.insert(tk.END, msg_record + "\n")
                self.log_textbox.configure(state="disabled")
                self.log_textbox.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_log_queue)

    def start_crawling(self):
        self.last_raw_csv_path = None
        province_chinese = self.province_menu.get()
        province_pinyin = PROVINCE_PINYIN_MAP.get(province_chinese)
        keyword = self.keyword_entry.get().strip()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        if not all([province_pinyin, keyword, start_date, end_date]):
            messagebox.showerror("输入错误", "所有字段均为必填项。")
            return

        self.task_start("正在爬取...")
        logging.info(f"🚀 开始爬取: 省份={province_chinese}, 关键词='{keyword}', 日期范围={start_date} to {end_date}")

        threading.Thread(
            target=self.run_crawl_task,
            args=(province_pinyin, province_chinese, keyword, start_date, end_date),
            daemon=True
        ).start()

    def run_crawl_task(self, province_pinyin, province_cn, keyword, start_date, end_date):
        try:
            # Fix: Pass arguments in the correct order using keywords for clarity
            start_crawl_process(
                province_pinyin,
                province_cn,
                keyword,
                start_date,
                end_date,
                output_dir=self.output_dir,
                log_queue=self.log_queue
            )
        except Exception:
            logging.error(f"爬取过程中发生严重错误")
            logging.error(traceback.format_exc())
            self.log_queue.put("CRAWL_FAILED")

    def run_conversion(self):
        logging.info("🔄 开始将 output 文件夹中的 CSV 文件转换为 Excel...")
        threading.Thread(target=self.run_conversion_task, daemon=True).start()

    def run_conversion_task(self):
        try:
            # Fix: Call the correct function
            run_converter(self.output_dir, self.log_queue)
            logging.info("✅ Excel 转换完成。")
        except Exception:
            logging.error("转换过程中发生错误")
            logging.error(traceback.format_exc())

    def start_formatting_thread(self):
        """Starts the report formatting process in a new thread."""
        if not self.last_raw_csv_path or not os.path.exists(self.last_raw_csv_path):
            messagebox.showerror("错误", "未找到有效的原始CSV文件。请先成功完成一次爬取。")
            return
        
        self.task_start("正在格式化报告...")
        logging.info(f"📄 开始格式化报告: {os.path.basename(self.last_raw_csv_path)}")

        threading.Thread(
            target=self.run_format_process_in_thread,
            args=(self.last_raw_csv_path,),
            daemon=True
        ).start()

    def run_format_process_in_thread(self, file_path):
        """
        Executes the main.py script as a subprocess to format the report.
        Captures and queues its output for real-time display in the GUI.
        """
        try:
            command = [sys.executable, 'main.py', '--format_report', file_path]
            # Use Popen for real-time output reading
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Redirect stderr to stdout
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            # Read output line by line
            for line in iter(process.stdout.readline, ''):
                self.root_logger.info(line.strip()) # Use logger to send to queue

            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.log_queue.put("FORMAT_COMPLETE")
            else:
                self.log_queue.put("FORMAT_FAILED")

        except Exception:
            self.root_logger.error("执行格式化子进程时发生严重错误。")
            self.root_logger.error(traceback.format_exc())
            self.log_queue.put("FORMAT_FAILED")

    def task_start(self, status_text):
        """Generic function to disable buttons and show progress when a task starts."""
        self.start_button.configure(state="disabled")
        self.convert_button.configure(state="disabled")
        self.format_button.configure(state="disabled")
        self.progressbar.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.progressbar.start()
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.configure(state="disabled")

    def task_complete(self, failed=False):
        """Generic function to re-enable buttons and stop progress when a task finishes."""
        self.progressbar.stop()
        self.progressbar.grid_forget()
        self.start_button.configure(state="normal")
        self.convert_button.configure(state="normal")
        # The format button is only enabled on crawl success, not here.
        if self.last_raw_csv_path and os.path.exists(self.last_raw_csv_path):
            self.format_button.configure(state="normal")
        else:
            self.format_button.configure(state="disabled")

        if failed:
            messagebox.showerror("任务失败", "任务执行失败，请检查日志获取详细信息。")
        else:
            # Only show success message if it wasn't a failure
            # messagebox.showinfo("任务完成", "任务已成功执行。") # This can be annoying
            pass

def main():
    # Set the script's directory as the current working directory
    # This is crucial for PyInstaller to find relative paths like 'main.py'
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Set up a fallback logger for GUI startup issues
    try:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        app = App()
        app.mainloop()
    except Exception as e:
        # If the GUI fails to start, log it to a file
        logging.basicConfig(filename='gui_startup_error.log', level=logging.ERROR,
                            format='%(asctime)s %(levelname)s:%(message)s')
        logging.error("GUI failed to start")
        logging.error(traceback.format_exc())
        # Also try to show a simple Tkinter message box
        try:
            root = tk.Tk()
            root.withdraw() # Hide the main window
            messagebox.showerror("严重错误", f"GUI启动失败: {e}\n详情请见 gui_startup_error.log")
        except:
            pass # If even Tkinter fails, we've done all we can.

if __name__ == "__main__":
    main()
