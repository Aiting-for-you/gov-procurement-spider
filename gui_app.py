import customtkinter
import tkinter
from tkinter import filedialog
from tkcalendar import DateEntry
from main import start_crawl_process
from converter import main as run_converter
import threading
import queue
import os
import glob

PROVINCE_PINYIN_MAP = {
    "安徽": "anhui", "重庆": "chongqing", "广东": "guangdong", "广西": "guangxi", 
    "河北": "hebei", "湖北": "hubei", "江苏": "jiangsu", "山东": "shandong", 
    "四川": "sichuan", "浙江": "zhejiang"
}
CHINESE_PROVINCES = list(PROVINCE_PINYIN_MAP.keys())

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("中国政府采购数据采集器")
        self.geometry("700x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        main_frame = customtkinter.CTkFrame(self)
        main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        controls_frame = customtkinter.CTkFrame(main_frame)
        controls_frame.pack(pady=10, padx=10, fill="x")

        province_label = customtkinter.CTkLabel(controls_frame, text="选择省份:")
        province_label.pack(side="left", padx=10, pady=10)
        self.optionmenu = customtkinter.CTkOptionMenu(controls_frame, values=CHINESE_PROVINCES)
        self.optionmenu.pack(side="left", padx=0, pady=10)

        keyword_label = customtkinter.CTkLabel(controls_frame, text="关键词:")
        keyword_label.pack(side="left", padx=10, pady=10)
        self.keyword_entry = customtkinter.CTkEntry(controls_frame, placeholder_text="例如：中标公告")
        self.keyword_entry.pack(side="left", padx=0, pady=10, fill="x", expand=True)
        
        date_frame = customtkinter.CTkFrame(main_frame)
        date_frame.pack(pady=10, padx=10, fill="x")

        start_date_label = customtkinter.CTkLabel(date_frame, text="开始日期:")
        start_date_label.pack(side="left", padx=10, pady=10)
        self.start_date_entry = DateEntry(date_frame, date_pattern='y-mm-dd', width=12, background='darkblue', foreground='white', borderwidth=2)
        self.start_date_entry.pack(side="left", padx=(0, 20), pady=10)

        end_date_label = customtkinter.CTkLabel(date_frame, text="结束日期:")
        end_date_label.pack(side="left", padx=10, pady=10)
        self.end_date_entry = DateEntry(date_frame, date_pattern='y-mm-dd', width=12, background='darkblue', foreground='white', borderwidth=2)
        self.end_date_entry.pack(side="left", padx=0, pady=10)

        output_dir_frame = customtkinter.CTkFrame(main_frame)
        output_dir_frame.pack(pady=10, padx=10, fill="x")

        self.select_dir_button = customtkinter.CTkButton(output_dir_frame, text="选择保存目录", command=self.select_output_directory)
        self.select_dir_button.pack(side="left", padx=(0, 10))

        self.output_directory = os.path.abspath("output")
        self.output_dir_label = customtkinter.CTkLabel(output_dir_frame, text="保存位置: " + self.output_directory, anchor="w")
        self.output_dir_label.pack(side="left", fill="x", expand=True)

        button_frame = customtkinter.CTkFrame(main_frame)
        button_frame.pack(pady=10, padx=10, fill="x")

        self.button = customtkinter.CTkButton(button_frame, text="开始爬取", command=self.start_crawling)
        self.button.pack(side="left", padx=(0, 5), expand=True, fill="x")

        self.convert_button = customtkinter.CTkButton(button_frame, text="将结果转为Excel", command=self.run_conversion, state="disabled")
        self.convert_button.pack(side="right", padx=(5, 0), expand=True, fill="x")

        self.log_textbox = customtkinter.CTkTextbox(main_frame, state="disabled", height=200, wrap="word")
        self.log_textbox.pack(pady=10, padx=10, fill="both", expand=True)

        self.log_queue = queue.Queue()
        self.after(100, self.process_log_queue)
        self.check_if_convertable()

    def select_output_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_directory = os.path.normpath(directory)
            self.output_dir_label.configure(text="保存位置: " + self.output_directory)
            self.check_if_convertable()

    def start_crawling(self):
        province_chinese = self.optionmenu.get()
        province_pinyin = PROVINCE_PINYIN_MAP.get(province_chinese)
        keyword = self.keyword_entry.get()
        start_date = self.start_date_entry.get_date().strftime('%Y-%m-%d')
        end_date = self.end_date_entry.get_date().strftime('%Y-%m-%d')

        if not all([province_pinyin, keyword, start_date, end_date]):
            tkinter.messagebox.showerror("错误", "所有字段都不能为空！")
            return

        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        self.button.configure(state="disabled", text="正在爬取...")
        self.convert_button.configure(state="disabled")

        threading.Thread(target=start_crawl_process, args=(
            province_pinyin, province_chinese, keyword, start_date, end_date,
            self.log_queue, self.output_directory
        ), daemon=True).start()

    def process_log_queue(self):
        try:
            while not self.log_queue.empty():
                msg = self.log_queue.get_nowait()
                if msg == "CRAWL_COMPLETE":
                    self.button.configure(state="normal", text="开始爬取")
                    self.log_message("爬取完成！结果已保存。")
                    self.check_if_convertable()
                elif msg == "CRAWL_FAILED":
                    self.button.configure(state="normal", text="开始爬取")
                    self.log_message("爬取失败，请检查日志。")
                else:
                    self.log_message(str(msg))
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_log_queue)

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.yview_moveto(1.0)

    def run_conversion(self):
        self.log_message("开始将CSV文件批量转换为Excel...")
        self.convert_button.configure(state="disabled")

        def conversion_thread():
            try:
                success = run_converter(target_directory=self.output_directory)
                if success:
                    self.log_message("转换完成。")
                else:
                    self.log_message("未找到可转换的CSV文件。")
            except Exception as e:
                self.log_message(f"转换过程中发生错误: {e}")
            finally:
                self.check_if_convertable()

        threading.Thread(target=conversion_thread, daemon=True).start()

    def check_if_convertable(self):
        try:
            csv_files = glob.glob(os.path.join(self.output_directory, '*.csv'))
            if csv_files:
                self.convert_button.configure(state="normal")
            else:
                self.convert_button.configure(state="disabled")
        except Exception as e:
            self.convert_button.configure(state="disabled")
            print(f"Error checking for CSV files: {e}")

    def on_closing(self):
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
