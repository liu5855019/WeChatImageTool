# -*- coding: utf-8 -*-
"""可复用 UI 小组件 (CustomTkinter)"""

import tkinter as tk
import customtkinter as ctk
from gui.utils import create_button


class SectionCard(ctk.CTkFrame):
    """带标题的卡片容器。内部用 self.body 放置内容（垂直堆叠）"""

    def __init__(self, master, title, **kwargs):
        super().__init__(master, fg_color="#FFFFFF", border_width=1,
                         border_color="#E5E7EB", corner_radius=10, **kwargs)
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#374151", anchor="w").pack(
            anchor="w", padx=16, pady=(12, 8))
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="x", padx=16, pady=(0, 14))


def browse_row(master, label_text, entry_var, browse_mode="dir",
               browse_title="选择目录", filetypes=None):
    """一行：标签 + 输入框 + 浏览按钮。browse_mode='dir' 或 'file'"""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(fill="x", pady=(0, 8))

    ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(size=12),
                 text_color="#6B7280", width=96, anchor="w").pack(side="left")

    entry = ctk.CTkEntry(row, textvariable=entry_var, font=ctk.CTkFont(size=12),
                         height=32, border_color="#E5E7EB", corner_radius=6)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def _pick():
        if browse_mode == "file":
            from tkinter import filedialog
            p = filedialog.askopenfilename(title=browse_title, filetypes=filetypes or [("所有文件", "*.*")])
        else:
            from tkinter import filedialog
            p = filedialog.askdirectory(title=browse_title)
        if p:
            entry_var.set(p)

    btn = create_button(row, "浏览", command=_pick, width=72, height=32)
    btn.pack(side="left")
    return entry


def labeled_field(master, label_text, entry_var, width=64):
    """一行：标签 + 窄输入框（用于数字/单位等小字段）"""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(side="left", pady=(0, 8))
    ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(size=12),
                 text_color="#6B7280").pack(side="left", padx=(0, 6))
    entry = ctk.CTkEntry(row, textvariable=entry_var, font=ctk.CTkFont(size=12),
                         height=32, width=width, border_color="#E5E7EB", corner_radius=6)
    entry.pack(side="left")
    return entry


def option_row(master, label_text, options, variable, width=110):
    """一行：标签 + 下拉框"""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(side="left", pady=(0, 8), padx=(12, 0))
    ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(size=12),
                 text_color="#6B7280").pack(side="left", padx=(0, 6))
    om = ctk.CTkOptionMenu(row, values=options, variable=variable,
                           width=width, height=32, corner_radius=6,
                           fg_color="#F3F4F6", button_color="#E5E7EB",
                           text_color="#374151", dropdown_fg_color="#FFFFFF")
    om.pack(side="left")
    return om
