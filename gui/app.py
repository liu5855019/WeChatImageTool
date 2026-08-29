# -*- coding: utf-8 -*-
"""主界面：构建窗口、卡片、日志区，并绑定核心逻辑（后台线程）"""

import threading
import tkinter as tk
import customtkinter as ctk

import config
from gui.utils import create_button, hide_console, ScrolledText
from gui.logging import GUILogger
from gui.widgets import SectionCard, browse_row, labeled_field
from core import file_ops
from core.downloader import WeChatDownloader, list_visible_windows
from core.naming import NamingScheme


NAMING_PRESETS = ['1001起序', '0001起序', '1起序', '日期+序号', '自定义']
MODE_MAP = {'剪贴板复制': 'clipboard', 'Ctrl+S 接管对话框': 'ctrl_s'}


class WeiXinImageToolGUI:
    def __init__(self, root):
        self.root = root
        root.title(config.GUI_CONF['window_title'])
        root.geometry(config.GUI_CONF['window_geometry'])
        root.resizable(True, True)

        # 变量
        self.var_img_folder = tk.StringVar(value=config.DEFAULTS['image_folder'])
        self.var_count = tk.StringVar(value=str(config.DEFAULTS['download_count']))
        self.var_dl_mode = tk.StringVar(value='剪贴板复制')  # '剪贴板复制' | 'Ctrl+S 接管对话框'
        self.var_naming_preset = tk.StringVar(value='1001起序')
        self.var_name_prefix = tk.StringVar(value='')
        self.var_name_start = tk.StringVar(value='1')
        self.var_name_digits = tk.StringVar(value='3')
        self.selected_hwnd = None                      # 用户手动选择的微信窗口句柄
        self.var_target_window = tk.StringVar(value="未选择")

        self.stop_event = threading.Event()
        self.worker = None

        self._build_ui()

    def _log(self, msg, level="info"):
        # 从后台线程经主线程写入，保证 tkinter 线程安全
        self.root.after(0, self.logger.log, msg, level)

    def _build_ui(self):
        # 主区恢复普通容器（不用可滚动，避免滚动条；窗口加高即可容纳全部内容）
        main = ctk.CTkFrame(self.root, fg_color="#F0F2F5")
        main.pack(fill="both", expand=True, padx=12, pady=12)

        # 标题区
        head = ctk.CTkFrame(main, fg_color="transparent")
        head.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(head, text=config.GUI_CONF['window_title'], font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#1A1A1A", anchor="w").pack(anchor="w")
        ctk.CTkLabel(head, text="保存微信图片到本地，自动命名整理",
                     font=ctk.CTkFont(size=12), text_color="#9CA3AF", anchor="w").pack(anchor="w", pady=(2, 0))

        # 路径设置（清空文件夹按钮合并到这一行，避免右侧大片空白）
        card_path = SectionCard(main, "路径设置")
        path_row = ctk.CTkFrame(card_path.body, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(path_row, text="图片保存文件夹", font=ctk.CTkFont(size=12),
                     text_color="#6B7280", width=96, anchor="w").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(path_row, textvariable=self.var_img_folder, font=ctk.CTkFont(size=12),
                     height=32, border_color="#E5E7EB", corner_radius=6).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        def _browse_folder():
            from tkinter import filedialog
            p = filedialog.askdirectory(title="选择图片保存文件夹")
            if p:
                self.var_img_folder.set(p)
        create_button(path_row, "浏览", command=_browse_folder, width=72, height=32).pack(side="left", padx=(0, 8))
        create_button(path_row, "清空文件夹", command=self._clear_folder,
                      width=96, height=32, style_type="warning").pack(side="left")
        card_path.pack(fill="x", pady=(0, 10))

        # ① 图片下载
        card_dl = SectionCard(main, "① 图片下载")

        # 数量 + 命名规则
        row_top = ctk.CTkFrame(card_dl.body, fg_color="transparent")
        row_top.pack(fill="x", pady=(0, 6))
        labeled_field(row_top, "下载数量", self.var_count, width=56)
        ctk.CTkLabel(row_top, text="命名规则", font=ctk.CTkFont(size=12),
                     text_color="#6B7280").pack(side="left", padx=(12, 6))
        self.naming_om = ctk.CTkOptionMenu(
            row_top, values=NAMING_PRESETS, variable=self.var_naming_preset,
            width=130, height=32, corner_radius=6, fg_color="#F3F4F6",
            button_color="#E5E7EB", text_color="#374151", dropdown_fg_color="#FFFFFF",
            command=self._on_naming_change)
        self.naming_om.pack(side="left")

        # 自定义字段（仅「自定义」时显示）
        self.custom_frame = ctk.CTkFrame(card_dl.body, fg_color="transparent")
        labeled_field(self.custom_frame, "前缀", self.var_name_prefix, width=80)
        labeled_field(self.custom_frame, "起始序号", self.var_name_start, width=64)
        labeled_field(self.custom_frame, "位数(0不补零)", self.var_name_digits, width=64)
        self.custom_frame.pack_forget()

        # 命名预览
        self.label_preview = ctk.CTkLabel(card_dl.body, text="", font=ctk.CTkFont(size=11),
                                          text_color="#6B7280", anchor="w")
        self.label_preview.pack(anchor="w", pady=(0, 6))

        # 下载方式
        mode_row = ctk.CTkFrame(card_dl.body, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(mode_row, text="下载方式", font=ctk.CTkFont(size=12),
                     text_color="#6B7280").pack(side="left", padx=(0, 6))
        ctk.CTkOptionMenu(mode_row, values=list(MODE_MAP.keys()), variable=self.var_dl_mode,
                          width=160, height=32, corner_radius=6, fg_color="#F3F4F6",
                          button_color="#E5E7EB", text_color="#374151",
                          dropdown_fg_color="#FFFFFF").pack(side="left")

        # 选择微信窗口（放在「开始下载」之前）
        pick_row = ctk.CTkFrame(card_dl.body, fg_color="transparent")
        pick_row.pack(fill="x", pady=(0, 6))
        create_button(pick_row, "选择微信窗口", command=self._pick_window,
                      width=120, height=34, style_type="secondary").pack(side="left")
        ctk.CTkLabel(pick_row, textvariable=self.var_target_window, font=ctk.CTkFont(size=11),
                     text_color="#9CA3AF", anchor="w").pack(side="left", padx=(10, 0))

        # 开始下载 / 停止
        dl_row = ctk.CTkFrame(card_dl.body, fg_color="transparent")
        dl_row.pack(fill="x", pady=(0, 6))
        self.btn_download = create_button(dl_row, "开始下载", command=self._start_download, width=120, height=34)
        self.btn_download.pack(side="left", padx=(0, 0))
        self.btn_stop = create_button(dl_row, "停止", command=self._stop_download, width=80, height=34,
                                      style_type="danger")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_stop.configure(state="disabled")

        # 操作说明
        ctk.CTkLabel(
            card_dl.body,
            text="提示：先点「选择微信窗口」选中微信图片查看器，再点「开始下载」。"
                 "3 秒倒计时内点击微信窗口使其置顶，工具会自动逐张保存。"
                 "推荐用「剪贴板复制」模式，最稳定；Ctrl+S 模式用于兼容旧版微信。",
            font=ctk.CTkFont(size=11), text_color="#9CA3AF", anchor="w", justify="left",
            wraplength=620).pack(anchor="w", pady=(2, 0))
        card_dl.pack(fill="x", pady=(0, 10))

        # ② 运行日志（可折叠，避免拖边框看日志）
        self.card_log = SectionCard(main, "② 运行日志")
        self.btn_toggle_log = create_button(
            self.card_log.body, "收起日志 ▲", command=self._toggle_log,
            width=96, height=28, style_type="secondary")
        self.btn_toggle_log.pack(anchor="w", pady=(0, 6))
        # 固定高度容器，保证日志区始终可见（不受卡片 body 仅横向撑开的影响）
        log_box = ctk.CTkFrame(self.card_log.body, fg_color="transparent", height=200)
        log_box.pack(fill="x", pady=(0, 2))
        log_box.pack_propagate(False)
        self.log_widget = ScrolledTextSafe(log_box, height=120)
        self.log_widget.pack(fill="both", expand=True)
        self.card_log.pack(fill="x", pady=(0, 0))

        self._log_collapsed = False
        self.logger = GUILogger(self.log_widget.text_widget)

        self._on_naming_change(self.var_naming_preset.get())  # 初始化预览 / 自定义栏显隐

    # ---------- 命名规则 ----------
    def _on_naming_change(self, preset):
        if preset == '自定义':
            self.custom_frame.pack(fill="x", pady=(0, 6))
        else:
            self.custom_frame.pack_forget()
        self._update_naming_preview()

    def _build_naming_from_ui(self):
        preset = self.var_naming_preset.get()
        if preset == '自定义':
            prefix = self.var_name_prefix.get().strip()
            try:
                start = int(self.var_name_start.get())
            except ValueError:
                start = 1
            try:
                digits = int(self.var_name_digits.get())
            except ValueError:
                digits = 3
            if digits < 0:
                digits = 0
            return NamingScheme('自定义', prefix=prefix, start=start, digits=digits, date=False)
        return NamingScheme.from_preset(preset)

    def _update_naming_preview(self):
        try:
            scheme = self._build_naming_from_ui()
            examples = scheme.preview(3)
            self.label_preview.configure(text="命名示例：" + ", ".join(f"{e}.jpg" for e in examples))
        except Exception:
            self.label_preview.configure(text="命名示例：—")

    # ---------- 动作 ----------
    def _start_download(self):
        try:
            count = int(self.var_count.get())
        except ValueError:
            self._log("下载数量必须为整数", "error")
            return
        folder = self.var_img_folder.get().strip()
        if not folder:
            self._log("请先设置图片保存文件夹", "error")
            return

        naming = self._build_naming_from_ui()

        self.stop_event.clear()
        self.btn_download.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._log("开始下载任务…", "info")
        if self.selected_hwnd:
            self._log(f"已使用手动选择的窗口：{self.var_target_window.get()}", "info")
        else:
            self._log("未选择窗口，将自动捕获前台窗口（请确保微信已置顶）", "warning")

        dl_mode = MODE_MAP.get(self.var_dl_mode.get(), 'clipboard')
        downloader = WeChatDownloader(
            image_folder=folder, count=count, wechat_save_src=config.DEFAULTS['wechat_save_src'],
            next_key=config.DEFAULTS['next_key'], naming=naming,
            log_cb=self._log, stop_event=self.stop_event, selected_hwnd=self.selected_hwnd,
            mode=dl_mode
        )
        self.worker = threading.Thread(target=self._run_download, args=(downloader,), daemon=True)
        self.worker.start()

    def _pick_window(self):
        """弹出模态列表，让用户从可见窗口中点选微信图片查看器"""
        wins = list_visible_windows(exclude_hwnd=self.root.winfo_id())
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("选择微信窗口")
        dlg.geometry("440x380")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.attributes("-topmost", True)
        dlg.configure(fg_color="#FFFFFF")

        ctk.CTkLabel(dlg, text="点选微信图片查看器窗口：",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#374151", anchor="w").pack(anchor="w", padx=14, pady=(12, 8))

        if not wins:
            ctk.CTkLabel(dlg, text="（没有检测到可见窗口，请先打开微信图片查看器）",
                         font=ctk.CTkFont(size=11), text_color="#EF4444").pack(anchor="w", padx=14)
            ctk.CTkButton(dlg, text="关闭", width=100, height=32,
                          command=dlg.destroy).pack(anchor="e", padx=14, pady=12)
            return

        sf = ctk.CTkScrollableFrame(dlg, fg_color="#F9FAFB", corner_radius=8)
        sf.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        def make_choose(hwnd, title):
            def _choose():
                self.selected_hwnd = hwnd
                self.var_target_window.set(title[:60])
                self._log(f"已选择窗口：{title[:40]}", "success")
                dlg.destroy()
            return _choose

        for hwnd, title in wins:
            ctk.CTkButton(
                sf, text=(title[:58] or f"（无标题 {hwnd}）"),
                height=34, corner_radius=6, anchor="w",
                fg_color="#FFFFFF", hover_color="#EFF6FF",
                text_color="#374151", border_color="#E5E7EB", border_width=1,
                command=make_choose(hwnd, title)
            ).pack(fill="x", padx=6, pady=3)

    def _run_download(self, downloader):
        downloader.run()
        self.root.after(0, self._on_download_done)

    def _on_download_done(self):
        self.btn_download.configure(state="normal")
        self.btn_stop.configure(state="disabled")

    def _stop_download(self):
        self.stop_event.set()
        self._log("正在停止…", "warning")

    def _clear_folder(self):
        folder = self.var_img_folder.get().strip()
        if not folder:
            self._log("请先设置图片保存文件夹", "error")
            return
        cnt = file_ops.clear_folder(folder)
        self._log(f"已清空文件夹，删除 {cnt} 张图片", "success")

    def _toggle_log(self):
        """折叠/展开运行日志卡片，省去拖拽窗口边框"""
        if self._log_collapsed:
            self.log_widget.pack(fill="both", expand=True)
            self.card_log.pack(fill="x", pady=(0, 0))
            self.btn_toggle_log.configure(text="收起日志 ▲")
            self._log_collapsed = False
        else:
            self.log_widget.pack_forget()
            self.card_log.pack(fill="x", pady=(0, 0))
            self.btn_toggle_log.configure(text="展开日志 ▼")
            self._log_collapsed = True


# ScrolledText 的安全封装（暴露内部 tk.Text 给 GUILogger）
class ScrolledTextSafe:
    def __init__(self, master, height=120):
        self._st = ScrolledText(master, height=height, bg="#1E1E1E", fg="#D4D4D4")
        self._st.pack(fill="both", expand=True)
        self.text_widget = self._st.text

    def pack(self, **kwargs):
        self._st.pack(**kwargs)

    def pack_forget(self):
        self._st.pack_forget()


def main():
    ctk.set_appearance_mode(config.GUI_CONF['appearance_mode'])
    ctk.set_default_color_theme(config.GUI_CONF['color_theme'])
    hide_console()
    root = ctk.CTk()
    WeiXinImageToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
