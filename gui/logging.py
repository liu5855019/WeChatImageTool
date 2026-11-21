# -*- coding: utf-8 -*-
"""GUI 日志模块 (CustomTkinter 版, 复用自 1688 工具框架)

每条日志加 ``HH:mm:ss.SSS`` 时间戳前缀，并同步写入本地日志文件（按天分割）。
写文件失败时静默降级，不影响 GUI 显示。
"""

import os
import sys
import tkinter as tk
from datetime import datetime

from gui.utils import ScrolledText
from config import GUI_CONF, LOG_CONF


def _log_dir():
    """日志目录：配置优先；留空则用程序所在目录（打包后 exe 同目录，开发时项目根目录）。"""
    configured = LOG_CONF.get('dir')
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'logs')


class GUILogger:
    """多色日志写入文本控件，线程不安全，调用方需在主线程执行或经 root.after 转发"""

    def __init__(self, log_text_widget):
        self.log_text = log_text_widget
        self._init_log_tags()
        self.log_file = None
        if LOG_CONF.get('enabled', True):
            self._open_log_file()

    def _open_log_file(self):
        try:
            log_dir = _log_dir()
            os.makedirs(log_dir, exist_ok=True)
            path = os.path.join(log_dir, f"wechat_tool_{datetime.now():%Y-%m-%d}.log")
            self.log_file = open(path, 'a', encoding='utf-8')
            self.log_file.write(f"\n===== 启动 {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
            self.log_file.flush()
        except Exception:
            self.log_file = None

    def _init_log_tags(self):
        for log_type, color in GUI_CONF['log_colors'].items():
            self.log_text.tag_configure(color, foreground=color)

    def log(self, message, message_type="info"):
        # 毫秒时间戳：%f 是 6 位微秒，截前 3 位得 SSS
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        line = f"{ts} {message}"

        self.log_text.config(state=tk.NORMAL)
        color = GUI_CONF['log_colors'].get(message_type, "white")
        self.log_text.tag_configure(color, foreground=color)
        self.log_text.insert(tk.END, line + "\n", color)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

        # 同步到本地文件：额外带级别，便于事后排查（纯文本无颜色区分）
        if self.log_file:
            try:
                self.log_file.write(f"{ts} [{message_type.upper()}] {message}\n")
                self.log_file.flush()
            except Exception:
                pass

    def clear(self):
        """只清空 GUI 显示，日志文件保留。"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def close(self):
        """关闭日志文件句柄（窗口关闭时调用）。"""
        if self.log_file:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None
