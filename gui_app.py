import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkcalendar import Calendar
import threading
import queue
import os
from datetime import datetime
import sys
import logging
import traceback

# Import project-specific modules
from logger_config import QueueHandler
from main import start_crawl_process
from converter import run_converter
from report_generator import format_report_from_path
from cleaner import clean_report_by_keywords
from province_mapping import PROVINCE_PINYIN_MAP, get_chinese_province_list
from driver_setup import quit_webdriver # Import the new quit function

class GuiApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("中国政府采购数据采集器")
        self.geometry("700x650")

        # --- Base Path & Output Dir ---
        self.base_path = self.get_base_path()
        self.output_dir = os.path.join(self.base_path, "output")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # --- State Variables ---
        # No longer need to store the driver instance here
        self.last_raw_csv_path = None
        self.files_to_convert = []

        # --- UI Setup ---
        self.setup_ui()
        
        # --- Logging Setup ---
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        self.root_logger = logging.getLogger()
        self.root_logger.setLevel(logging.INFO)
        self.root_logger.addHandler(self.queue_handler)
        self.after(100, self.process_log_queue)
        
        # --- Window Close Handler ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_base_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # --- Input Frame ---
        input_frame = ctk.CTkFrame(self)
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Province
        province_label = ctk.CTkLabel(input_frame, text="省份:")
        province_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.province_menu = ctk.CTkOptionMenu(input_frame, values=get_chinese_province_list())
        self.province_menu.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Keyword
        keyword_label = ctk.CTkLabel(input_frame, text="关键词:")
        keyword_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.keyword_entry = ctk.CTkEntry(input_frame, placeholder_text="例如: 空调")
        self.keyword_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Start Date
        start_date_label = ctk.CTkLabel(input_frame, text="开始日期:")
        start_date_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.start_date_entry = ctk.CTkEntry(input_frame)
        self.start_date_entry.grid(row=2, column=1, padx=(10,0), pady=5, sticky="ew")
        start_date_button = ctk.CTkButton(input_frame, text="📅", width=30, command=lambda: self.open_calendar(self.start_date_entry))
        start_date_button.grid(row=2, column=2, padx=(5,10), pady=5)

        # End Date
        end_date_label = ctk.CTkLabel(input_frame, text="结束日期:")
        end_date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.end_date_entry = ctk.CTkEntry(input_frame)
        self.end_date_entry.grid(row=3, column=1, padx=(10,0), pady=5, sticky="ew")
        end_date_button = ctk.CTkButton(input_frame, text="📅", width=30, command=lambda: self.open_calendar(self.end_date_entry))
        end_date_button.grid(row=3, column=2, padx=(5,10), pady=5)
        
        today = datetime.now()
        self.start_date_entry.insert(0, today.replace(day=1).strftime("%Y-%m-%d"))
        self.end_date_entry.insert(0, today.strftime("%Y-%m-%d"))

        # --- Action Frame ---
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.crawl_button = ctk.CTkButton(self.action_frame, text="开始爬取", command=self.start_crawling)
        self.crawl_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.format_button = ctk.CTkButton(self.action_frame, text="生成规范报告", command=self.start_formatting, state="disabled")
        self.format_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.convert_button = ctk.CTkButton(self.action_frame, text="将结果转为Excel", command=self.run_conversion)
        self.convert_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.clean_button = ctk.CTkButton(self.action_frame, text="清洗报告数据", command=self.run_cleaning)
        self.clean_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # --- Progress Frame ---
        self.progress_frame = ctk.CTkFrame(self)
        self.progressbar = ctk.CTkProgressBar(self.progress_frame)
        self.progressbar.set(0)

        # --- Log Frame ---
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

    def open_calendar(self, entry_widget):
        cal_win = ctk.CTkToplevel(self)
        cal_win.title("选择日期")
        cal_win.transient(self)
        cal_win.grab_set()
        try:
            current_date = datetime.strptime(entry_widget.get(), "%Y-%m-%d")
        except ValueError:
            current_date = datetime.now()
        cal = Calendar(cal_win, selectmode='day', year=current_date.year, month=current_date.month, day=current_date.day, date_pattern='yyyy-mm-dd')
        cal.pack(padx=10, pady=10)
        def on_date_select():
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, cal.get_date())
            cal_win.destroy()
        ctk.CTkButton(cal_win, text="确定", command=on_date_select).pack(pady=10)

    def process_log_queue(self):
        try:
            while True:
                msg_record = self.log_queue.get_nowait()
                if msg_record == "CRAWL_COMPLETE":
                    self.task_complete()
                    self.last_raw_csv_path = self.find_latest_raw_csv()
                    if self.last_raw_csv_path:
                        self.root_logger.info(f"爬取完成，可对 {os.path.basename(self.last_raw_csv_path)} 生成报告。")
                        self.format_button.configure(state="normal")
                    else:
                        self.root_logger.warning("爬取任务结束，但未找到任何原始数据文件。")
                elif msg_record == "CRAWL_FAILED":
                    self.task_complete(failed=True)
                elif msg_record in ["FORMAT_COMPLETE", "FORMAT_FAILED", "CONVERT_COMPLETE", "TASK_COMPLETE"]:
                    self.task_complete(failed="FAILED" in msg_record)
                else:
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert(tk.END, msg_record + "\n")
                    self.log_textbox.configure(state="disabled")
                    self.log_textbox.see(tk.END)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_log_queue)

    def task_start(self, message):
        self.crawl_button.configure(state="disabled")
        self.convert_button.configure(state="disabled")
        self.format_button.configure(state="disabled")
        self.clean_button.configure(state="disabled")
        self.progress_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.progressbar.start()
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.insert("1.0", message + "\n\n")
        self.log_textbox.configure(state="disabled")

    def task_complete(self, failed=False):
        self.progressbar.stop()
        self.progress_frame.grid_forget()
        self.crawl_button.configure(state="normal")
        self.convert_button.configure(state="normal")
        self.clean_button.configure(state="normal")
        if self.last_raw_csv_path: # Re-enable format button if a file exists
            self.format_button.configure(state="normal")
        if failed:
            messagebox.showerror("任务失败", "任务执行失败，请检查日志获取详细信息。")

    def start_crawling(self):
        province = self.province_menu.get()
        keyword = self.keyword_entry.get().strip()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()
        if not all([province, keyword, start_date, end_date]):
            messagebox.showerror("输入错误", "所有字段均为必填项。")
            return
        self.task_start(f"正在爬取: 省份={province}, 关键词='{keyword}'...")
        threading.Thread(target=self.run_crawl_task, args=(province, keyword, start_date, end_date), daemon=True).start()

    def run_crawl_task(self, province, keyword, start_date, end_date):
        try:
            province_pinyin = PROVINCE_PINYIN_MAP[province]
            # The crawl process no longer returns a driver
            start_crawl_process(province_pinyin, province, keyword, start_date, end_date, self.output_dir, self.log_queue)
        except Exception as e:
            self.root_logger.error(f"爬取过程中发生严重错误: {e}\n{traceback.format_exc()}")
            self.log_queue.put("CRAWL_FAILED")
        finally:
            self.log_queue.put("CRAWL_COMPLETE")

    def start_formatting(self):
        if not self.last_raw_csv_path or not os.path.exists(self.last_raw_csv_path):
            messagebox.showerror("错误", "未找到有效的原始CSV文件。请先成功完成一次爬取。")
            return
        self.task_start(f"正在格式化报告: {os.path.basename(self.last_raw_csv_path)}")
        threading.Thread(target=self.run_format_task, args=(self.last_raw_csv_path,), daemon=True).start()

    def run_format_task(self, file_path):
        try:
            result_path = format_report_from_path(file_path, logger=self.root_logger)
            if result_path:
                self.files_to_convert.clear()
                base_name = os.path.splitext(file_path)[0]
                processed_path = f"{base_name}_processed.csv"
                self.files_to_convert.append(file_path)
                if os.path.exists(processed_path): self.files_to_convert.append(processed_path)
                self.files_to_convert.append(result_path)
                self.log_queue.put("FORMAT_COMPLETE")
                self.root_logger.info(f"报告生成完毕，已准备 {len(self.files_to_convert)} 个文件用于后续转换。")
            else:
                self.log_queue.put("FORMAT_FAILED")
        except Exception as e:
            self.root_logger.error(f"格式化时发生严重错误: {e}\n{traceback.format_exc()}")
            self.log_queue.put("FORMAT_FAILED")

    def run_conversion(self):
        if not self.files_to_convert:
            messagebox.showwarning('操作无效', '没有找到可供转换的文件列表。\n\n请先成功运行一次"生成规范报告"。')
            return
        self.task_start("正在批量转换...")
        threading.Thread(target=self.run_conversion_task, daemon=True).start()

    def run_conversion_task(self):
        try:
            status, summary = run_converter(self.files_to_convert)
            self.root_logger.info(summary)
            messagebox.showinfo("转换结果", summary)
        except Exception as e:
            self.root_logger.error(f"转换时发生未知错误: {e}\n{traceback.format_exc()}")
        finally:
            self.log_queue.put("CONVERT_COMPLETE")

    def run_cleaning(self):
        file_path = filedialog.askopenfilename(title="选择要清洗的报告文件", filetypes=[("CSV Report", "*_report.csv")], initialdir=self.output_dir)
        if not file_path: return
        keywords = ['维保', '服务']
        self.task_start(f"正在清洗文件: {os.path.basename(file_path)}")
        threading.Thread(target=self.run_cleaning_task, args=(file_path, keywords), daemon=True).start()

    def run_cleaning_task(self, file_path, keywords):
        try:
            status, summary = clean_report_by_keywords(file_path, keywords, self.root_logger)
            self.root_logger.info(summary)
            messagebox.showinfo("清洗结果", summary)
        except Exception as e:
            self.root_logger.error(f"清洗时发生未知错误: {e}\n{traceback.format_exc()}")
        finally:
            self.log_queue.put("TASK_COMPLETE")

    def find_latest_raw_csv(self):
        try:
            files = [os.path.join(self.output_dir, f) for f in os.listdir(self.output_dir) if f.endswith('.csv') and '_report' not in f and '_processed' not in f]
            return max(files, key=os.path.getctime) if files else None
        except Exception as e:
            self.root_logger.error(f"查找最新CSV时出错: {e}")
            return None

    def on_closing(self):
        if messagebox.askokcancel("退出", "确定要退出程序吗？"):
            # Use the new centralized quit function
            self.root_logger.info("正在通过管理器关闭浏览器...")
            quit_webdriver()
            self.destroy()

def main():
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        app = GuiApp()
        app.mainloop()
    except Exception as e:
        logging.basicConfig(filename='gui_startup_error.log', level=logging.ERROR, format='%(asctime)s %(levelname)s:%(message)s')
        logging.error(f"GUI failed to start: {e}\n{traceback.format_exc()}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("严重错误", f"GUI启动失败: {e}\n详情请见 gui_startup_error.log")

if __name__ == "__main__":
    main()
