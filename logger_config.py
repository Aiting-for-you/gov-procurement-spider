import logging
import sys
from logging.handlers import TimedRotatingFileHandler

def get_logger(name, log_file='app.log'):
    """
    配置并返回一个日志记录器。
    - 输出到控制台
    - 按天滚动记录到文件
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # 如果已经配置过，直接返回

    logger.setLevel(logging.INFO)

    # 创建一个格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 创建一个用于写入日志文件的处理器
    # TimedRotatingFileHandler 会按天自动分割日志文件
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # 创建一个用于输出到控制台的处理器
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # 将处理器添加到日志记录器
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger

class QueueHandler(logging.Handler):
    """
    一个自定义的日志处理器，可以将日志记录发送到队列中，
    供 GUI 线程安全地读取和显示。
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record)) 