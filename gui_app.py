import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry
import threading
import os
from datetime import datetime

from main import start_crawl_process

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("中国政府采购网爬虫")
        self.geometry("800x600")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Frames ---
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        # --- Control Frame Widgets ---
        self.control_frame.grid_columnconfigure(1, weight=1)

        # Province
        self.province_label = ctk.CTkLabel(self.control_frame, text="选择省份:")
        self.province_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # --- 省份映射 ---
        self.province_map = {
            'anhui': '安徽', 'chongqing': '重庆', 'guangdong': '广东', 'guangxi': '广西', 
            'hebei': '河北', 'hubei': '湖北', 'jiangsu': '江苏', 'shandong': '山东', 
            'sichuan': '四川', 'zhejiang': '浙江'
            # 后续新增省份可在此处添加
        }
        
        parsers_dir = os.path.join(os.path.dirname(__file__), 'detail_parsers')
        province_pinyins = sorted([f.replace('.py', '') for f in os.listdir(parsers_dir) if f.endswith('.py') and not f.startswith('__') and f != 'base.py' and f != 'test.py'])
        
        self.province_options_cn = [self.province_map.get(p, p.capitalize()) for p in province_pinyins]
        self.pinyin_map_cn = {self.province_map.get(p, p.capitalize()): p for p in province_pinyins}
        
        self.province_menu = ctk.CTkOptionMenu(self.control_frame, values=self.province_options_cn)
        self.province_menu.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # Keyword
        self.keyword_label = ctk.CTkLabel(self.control_frame, text="关键词:")
        self.keyword_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.keyword_entry = ctk.CTkEntry(self.control_frame, placeholder_text="例如：空调")
        self.keyword_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.keyword_entry.insert(0, "空调")

        # Start Date
        self.start_date_label = ctk.CTkLabel(self.control_frame, text="开始日期:")
        self.start_date_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        today = datetime.now()
        self.start_date_entry = DateEntry(self.control_frame, date_pattern='y-mm-dd', year=today.year, month=today.month, day=1)
        self.start_date_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # End Date
        self.end_date_label = ctk.CTkLabel(self.control_frame, text="结束日期:")
        self.end_date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.end_date_entry = DateEntry(self.control_frame, date_pattern='y-mm-dd')
        self.end_date_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        # Start Button
        self.start_button = ctk.CTkButton(self.control_frame, text="开始爬取", command=self.start_crawling_thread)
        self.start_button.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

        # --- Log Frame Widgets ---
        self.log_textbox = ctk.CTkTextbox(self.log_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.crawling_thread = None

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert(tk.END, message + "\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see(tk.END)

    def start_crawling_thread(self):
        province_cn = self.province_menu.get()
        province_pinyin = self.pinyin_map_cn.get(province_cn)
        keyword = self.keyword_entry.get().strip()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        if not keyword:
            messagebox.showerror("错误", "关键词不能为空！")
            return

        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", tk.END)
        self.log_textbox.configure(state="disabled")
        
        self.start_button.configure(state="disabled", text="正在爬取...")

        self.crawling_thread = threading.Thread(
            target=self.run_crawl, 
            args=(province_pinyin, province_cn, keyword, start_date, end_date)
        )
        self.crawling_thread.daemon = True
        self.crawling_thread.start()

    def run_crawl(self, province_pinyin, province_cn, keyword, start_date, end_date):
        try:
            # A simple logger function that the core process can call
            def gui_logger(message):
                self.after(0, self.log, message)

            start_crawl_process(
                province_pinyin=province_pinyin,
                province_cn=province_cn,
                keyword=keyword,
                start_date=start_date,
                end_date=end_date,
                logger=gui_logger
            )
            self.after(0, messagebox.showinfo, "完成", "爬取任务已完成！")
        except Exception as e:
            self.after(0, messagebox.showerror, "失败", f"爬取过程中发生错误: {e}")
        finally:
            self.after(0, self.reset_ui)
    
    def reset_ui(self):
        self.start_button.configure(state="normal", text="开始爬取")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')
    app = App()
    app.mainloop() 