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


# --- Constants ---
# The single source of truth for provinces is now province_mapping.py
CHINESE_PROVINCES = get_chinese_province_list()


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
        self.output_dir = os.path.abspath("output")
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
        if not self.last_raw_csv_path or not os.path.exists(self.last_raw_csv_path):
            messagebox.showerror("错误", "找不到可用的原始数据文件进行格式化。")
            return

        self.task_start("正在格式化...")
        logging.info(f"--- 开始对 {os.path.basename(self.last_raw_csv_path)} 进行规范化 ---")
        
        threading.Thread(
            target=self.run_format_process_in_thread,
            args=(self.last_raw_csv_path,),
            daemon=True
        ).start()

    def run_format_process_in_thread(self, file_path):
        command = [sys.executable, "main.py", "--format_report", file_path]
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            for line in iter(process.stdout.readline, ''):
                logging.info(line.strip())
            process.stdout.close()
            process.wait()
            
            if process.returncode == 0:
                self.log_queue.put("FORMAT_COMPLETE")
            else:
                self.log_queue.put("FORMAT_FAILED")
        except Exception:
            logging.error("格式化子进程启动或执行失败。")
            logging.error(traceback.format_exc())
            self.log_queue.put("FORMAT_FAILED")

    def task_start(self, status_text):
        """Generic function to call when a long-running task starts."""
        self.start_button.configure(state="disabled", text=status_text)
        self.format_button.configure(state="disabled")
        self.convert_button.configure(state="disabled")
        
        self.progressbar.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.progressbar.start()
        
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.configure(state="disabled")

    def task_complete(self, failed=False):
        """Generic function to call when a long-running task completes."""
        self.start_button.configure(state="normal", text="开始爬取")
        # Only re-enable format button if a file is available
        if self.last_raw_csv_path and os.path.exists(self.last_raw_csv_path):
            self.format_button.configure(state="normal")
        self.convert_button.configure(state="normal")
        
        self.progressbar.stop()
        self.progressbar.grid_forget()

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
