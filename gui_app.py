import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkcalendar import Calendar
import threading
import queue
import os
from datetime import datetime

# Import the main crawler process and the new converter utility
from main import start_crawl_process
from converter import run_converter

# --- Constants ---
# This makes it easier to add new provinces in the future
PROVINCE_PINYIN_MAP = {
    "安徽": "anhui", "重庆": "chongqing", "广东": "guangdong", "广西": "guangxi",
    "河北": "hebei", "湖北": "hubei", "江苏": "jiangsu", "山东": "shandong",
    "四川": "sichuan", "浙江": "zhejiang"
}
CHINESE_PROVINCES = list(PROVINCE_PINYIN_MAP.keys())


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("中国政府采购数据采集器")
        self.geometry("700x600")

        # --- Frame Setup ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1) # Allow entry widgets to expand

        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.action_frame.grid_columnconfigure((0, 1), weight=1)

        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
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

        # --- Custom Date Pickers ---
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

        # --- Log Widgets ---
        self.log_textbox = ctk.CTkTextbox(self.log_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

        # --- Threading & Queue Setup ---
        self.log_queue = queue.Queue()
        self.after(100, self.process_log_queue)

    def open_calendar(self, entry_widget):
        # Toplevel window for the calendar
        cal_win = ctk.CTkToplevel(self)
        cal_win.title("选择日期")
        cal_win.transient(self) # Keep on top of the main window
        cal_win.grab_set() # Modal

        # Get the current date from the entry to set the calendar's initial date
        try:
            current_date = datetime.strptime(entry_widget.get(), "%Y-%m-%d")
        except ValueError:
            current_date = datetime.now()
            
        cal = Calendar(cal_win, selectmode='day',
                       year=current_date.year, month=current_date.month, day=current_date.day,
                       date_pattern='yyyy-mm-dd',
                       background=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0],
                       foreground=ctk.ThemeManager.theme["CTkLabel"]["text_color"][0],
                       headersbackground=ctk.ThemeManager.theme["CTkButton"]["fg_color"][0],
                       headersforeground='white',
                       selectbackground=ctk.ThemeManager.theme["CTkButton"]["fg_color"][1],
                       normalbackground=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0],
                       weekendbackground=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0],
                       othermonthforeground='gray50',
                       othermonthbackground='gray85',
                       )
        cal.pack(padx=10, pady=10)

        def on_date_select():
            selected_date = cal.get_date()
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, selected_date)
            cal_win.destroy()

        ok_button = ctk.CTkButton(cal_win, text="确定", command=on_date_select)
        ok_button.pack(pady=10)

    def select_output_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir = directory
            self.output_dir_label.configure(text=f"保存在: {self.output_dir}")

    def log(self, message):
        """Helper to safely log messages from any thread."""
        self.log_queue.put(message)

    def process_log_queue(self):
        """Processes messages from the log queue to update the UI."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "CRAWL_COMPLETE" or msg == "CRAWL_FAILED":
                    self.start_button.configure(state="normal", text="开始爬取")
                    if msg == "CRAWL_COMPLETE":
                        self.log("✅ 爬取任务完成。")
                    else: # CRAWL_FAILED
                        self.log("❌ 爬取任务失败，请检查日志。")
                else:
                    self.log_textbox.configure(state="normal")
                    self.log_textbox.insert(tk.END, str(msg) + "\n")
                    self.log_textbox.configure(state="disabled")
                    self.log_textbox.see(tk.END)
        except queue.Empty:
            pass  # No messages in queue
        finally:
            self.after(100, self.process_log_queue)

    def start_crawling(self):
        province_chinese = self.province_menu.get()
        province_pinyin = PROVINCE_PINYIN_MAP.get(province_chinese)
        keyword = self.keyword_entry.get().strip()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        if not all([province_pinyin, keyword, start_date, end_date]):
            messagebox.showerror("输入错误", "所有字段均为必填项。")
            return

        # Disable button to prevent multiple runs
        self.start_button.configure(state="disabled", text="正在爬取...")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.configure(state="disabled")
        
        self.log(f"🚀 开始爬取任务: 省份={province_chinese}, 关键词='{keyword}', 日期范围={start_date} to {end_date}")

        # Run crawling in a separate thread to keep the GUI responsive
        crawl_thread = threading.Thread(
            target=self.run_crawl_task,
            args=(province_pinyin, province_chinese, keyword, start_date, end_date),
            daemon=True
        )
        crawl_thread.start()

    def run_crawl_task(self, province_pinyin, province_cn, keyword, start_date, end_date):
        """The actual task that runs in a thread."""
        try:
            start_crawl_process(province_pinyin, province_cn, keyword, start_date, end_date, self, self.output_dir)
            self.log_queue.put("CRAWL_COMPLETE")
        except Exception as e:
            self.log(f"爬取过程中发生严重错误: {e}")
            self.log(f"详细信息: {traceback.format_exc()}")
            self.log_queue.put("CRAWL_FAILED")

    def run_conversion(self):
        """Runs the CSV to Excel conversion logic."""
        self.log("🔄 开始将 output 文件夹中的 CSV 文件转换为 Excel...")
        
        conversion_thread = threading.Thread(target=self.run_conversion_task, daemon=True)
        conversion_thread.start()

    def run_conversion_task(self):
        try:
            # The converter function will now handle its own logging via the queue
            run_converter(self.output_dir, self)
        except Exception as e:
            self.log(f"转换过程中发生错误: {e}")

if __name__ == "__main__":
    # Set appearance
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    app = App()
    app.mainloop()
