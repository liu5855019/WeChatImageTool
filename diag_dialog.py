# -*- coding: utf-8 -*-
"""诊断脚本：在微信保存对话框打开时运行，输出窗口句柄、类名、标题、子控件"""
import time
import win32gui
import win32con

print("2 秒后抓取所有窗口...")
time.sleep(2)

save_keywords = ('保存', '另存为', 'Save As', 'Save')
found = []

def enum_cb(hwnd, _):
    if win32gui.IsWindowVisible(hwnd):
        try:
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True
        is_save = cls == '#32770' and any(k in title for k in save_keywords)
        if is_save or any(k in title for k in save_keywords):
            found.append((hwnd, cls, title))
            print(f"\n[对话框] hwnd={hwnd} class='{cls}' title='{title}'")
            # 枚举子控件
            children = []
            def child_cb(ch, __):
                try:
                    c_cls = win32gui.GetClassName(ch)
                    c_txt = win32gui.GetWindowText(ch)
                    children.append((ch, c_cls, c_txt))
                except Exception:
                    pass
                return True
            win32gui.EnumChildWindows(hwnd, child_cb, None)
            for ch, c_cls, c_txt in children:
                marker = " <-- 文件名输入框" if c_cls == 'Edit' else ""
                print(f"  子控件 hwnd={ch} class='{c_cls}' text='{c_txt[:60]}'{marker}")
            # 尝试点中 Edit 读文本
            for ch, c_cls, c_txt in children:
                if c_cls == 'Edit':
                    try:
                        buf = win32gui.GetWindowText(ch)
                        print(f"  Edit 当前内容：'{buf}'")
                    except Exception as e:
                        print(f"  读取 Edit 失败：{e}")
    return True

win32gui.EnumWindows(enum_cb, None)

if not found:
    print("\n[警告] 没找到任何含保存关键词的窗口。打印所有顶层窗口供参考：")
    def all_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            try:
                print(f"  hwnd={hwnd} class='{win32gui.GetClassName(hwnd)}' title='{win32gui.GetWindowText(hwnd)}'")
            except Exception:
                pass
        return True
    win32gui.EnumWindows(all_cb, None)
else:
    print(f"\n共找到 {len(found)} 个相关窗口")

input("\n按回车退出...")
