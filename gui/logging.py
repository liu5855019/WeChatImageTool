# -*- coding: utf-8 -*-
"""GUI 日志模块 (CustomTkinter 版, 复用自 1688 工具框架)"""

import tkinter as tk
from gui.utils import ScrolledText
from config import GUI_CONF


class GUILogger:
    """多色日志写入文本控件，线程不安全，调用方需在主线程执行或经 root.after 转发"""

    def __init__(self, log_text_widget):
        self.log_text = log_text_widget
        self._init_log_tags()

    def _init_log_tags(self):
        for log_type, color in GUI_CONF['log_colors'].items():
            self.log_text.tag_configure(color, foreground=color)

    def log(self, message, message_type="info"):
        self.log_text.config(state=tk.NORMAL)
        color = GUI_CONF['log_colors'].get(message_type, "white")
        self.log_text.tag_configure(color, foreground=color)
        self.log_text.insert(tk.END, message + "\n", color)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)
