# -*- coding: utf-8 -*-
"""GUI 工具模块 (CustomTkinter 版, 复用自 1688 工具框架)"""

import ctypes
import os
import tkinter as tk
import customtkinter as ctk
from config import get_button_config, BUTTON_CONF


def create_button(master, text, command=None, style_type='primary', **kwargs):
    """统一风格按钮工厂"""
    config = get_button_config(style_type)
    width = kwargs.pop('width', config['width'])
    height = kwargs.pop('height', config['height'])
    corner_radius = kwargs.pop('corner_radius', config['corner_radius'])
    border_width = kwargs.pop('border_width', config['border_width'])
    fg_color = kwargs.pop('fg_color', config['fg_color'])
    hover_color = kwargs.pop('hover_color', config['hover_color'])
    text_color = kwargs.pop('text_color', config['text_color'])

    return ctk.CTkButton(
        master,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=corner_radius,
        border_width=border_width,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=text_color,
        **kwargs
    )


def hide_console():
    """隐藏控制台窗口（仅 Windows）"""
    if os.name == 'nt':
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd != 0:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                ctypes.windll.user32.UpdateWindow(hwnd)
        except Exception:
            pass


class ScrolledText:
    """CustomTkinter 兼容的滚动文本控件（用于日志区）"""

    def __init__(self, master=None, **kwargs):
        self.frame = ctk.CTkFrame(master, fg_color="transparent")

        self.scrollbar = ctk.CTkScrollbar(self.frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        width = kwargs.pop('width', 80)
        height = kwargs.pop('height', 24)
        bg_color = kwargs.pop('bg', '#1a1a1a')
        fg_color = kwargs.pop('fg', '#ffffff')

        self.text = tk.Text(
            self.frame,
            yscrollcommand=self.scrollbar.set,
            width=width,
            height=height,
            bg=bg_color,
            fg=fg_color,
            insertbackground=fg_color,
            selectbackground='#3a3a3a',
            relief=tk.FLAT,
            padx=10,
            pady=10,
            **kwargs
        )
        self.text.pack(fill=tk.BOTH, expand=True)
        self.scrollbar.configure(command=self.text.yview)

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def config(self, **kwargs):
        self.text.config(**kwargs)

    def configure(self, **kwargs):
        self.text.configure(**kwargs)

    def insert(self, *args, **kwargs):
        self.text.insert(*args, **kwargs)

    def see(self, *args, **kwargs):
        self.text.see(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.text.delete(*args, **kwargs)

    def tag_configure(self, *args, **kwargs):
        self.text.tag_configure(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.text.get(*args, **kwargs)

    def bind(self, *args, **kwargs):
        self.text.bind(*args, **kwargs)

    def winfo_children(self):
        return self.text.winfo_children()
