# -*- coding: utf-8 -*-
"""图片命名方案：预设方案 + 自定义，生成文件名基础名（不含扩展名）"""

import os
import re
import datetime
from config import IMAGE_EXTS


class NamingScheme:
    """命名方案：根据序号 seq 生成文件名基础名（不含扩展名）。

    预设方案：
      1001起序  -> 1001.jpg, 1002.jpg ...（4位定宽，起始1001）
      0001起序  -> 0001.jpg, 0002.jpg ...（4位定宽，起始1）
      1起序     -> 1.jpg, 2.jpg ...（不补零，起始1）
      日期+序号 -> 20260828_001.jpg ...（当天日期 + 3位序号）
      自定义    -> 用户自定义 前缀 + 起始序号 + 位数（如 wx_001.jpg）
    """

    PRESETS = {
        '1001起序':  {'prefix': '', 'start': 1001, 'digits': 4, 'date': False},
        '0001起序':  {'prefix': '', 'start': 1, 'digits': 4, 'date': False},
        '1起序':     {'prefix': '', 'start': 1, 'digits': 0, 'date': False},
        '日期+序号': {'prefix': '', 'start': 1, 'digits': 3, 'date': True},
        '自定义':    {'prefix': '', 'start': 1, 'digits': 3, 'date': False},
    }

    def __init__(self, preset='1001起序', prefix='', start=1, digits=3, date=False):
        self.preset = preset
        self.prefix = prefix
        self.start = start
        self.digits = digits
        self.date = date

    @classmethod
    def from_preset(cls, preset, prefix='', start=1, digits=3):
        p = cls.PRESETS.get(preset, cls.PRESETS['1001起序'])
        if preset == '自定义':
            return cls(preset, prefix=prefix, start=start, digits=digits, date=False)
        return cls(preset, prefix=p['prefix'], start=p['start'], digits=p['digits'], date=p['date'])

    def format(self, seq):
        """根据序号生成基础名（不含扩展名）"""
        if self.date:
            d = datetime.datetime.now().strftime('%Y%m%d')
            if self.prefix or (self.digits and self.digits > 0):
                return f"{d}_{self.prefix}{seq:0{self.digits}d}"
            return f"{d}_{seq:03d}"
        if self.digits and self.digits > 0:
            return f"{self.prefix}{seq:0{self.digits}d}"
        return f"{self.prefix}{seq}"

    def preview(self, count=3):
        """预览前几张的命名，用于 UI 展示"""
        return [self.format(self.start + i) for i in range(count)]


def compute_start(folder, scheme):
    """扫描文件夹，返回不覆盖已有文件的实际起始序号（>= 用户设定 start）。"""
    if not os.path.isdir(folder):
        return scheme.start
    if scheme.date:
        d = datetime.datetime.now().strftime('%Y%m%d')
        pat = re.compile(r'^' + re.escape(d) + r'_(\d+)$')
    else:
        esc = re.escape(scheme.prefix) if scheme.prefix else ''
        pat = re.compile(r'^' + esc + r'(\d+)$')
    max_seq = 0
    found = False
    for name in os.listdir(folder):
        ext = os.path.splitext(name)[1].lower()
        if ext not in IMAGE_EXTS:
            continue
        base = os.path.splitext(name)[0]
        m = pat.match(base)
        if m:
            try:
                seq = int(m.group(1))
            except Exception:
                continue
            max_seq = max(max_seq, seq)
            found = True
    if found and max_seq >= scheme.start:
        return max_seq + 1
    return scheme.start
