# -*- coding: utf-8 -*-
"""图片命名方案：预设方案 + 自定义，生成文件名基础名（不含扩展名）"""

import os
import re
import datetime
from config import IMAGE_EXTS


class NamingScheme:
    """命名方案：根据序号 seq（或媒体时间）生成文件名基础名（不含扩展名）。

    预设方案：
      文件日期   -> 20261120_212432.jpg（媒体时间；推测时间加 _dst 后缀）
      1001起序  -> 1001.jpg, 1002.jpg ...（4位定宽，起始1001）
      0001起序  -> 0001.jpg, 0002.jpg ...（4位定宽，起始1）
      1起序     -> 1.jpg, 2.jpg ...（不补零，起始1）
      日期+序号 -> 20260828_001.jpg ...（当天日期 + 3位序号）
      自定义    -> 用户自定义 前缀 + 起始序号 + 位数（如 wx_001.jpg）

    ``文件日期`` 是唯一依赖「媒体时间」的方案：下载时先用临时名落盘，取到
    拍摄/消息时间后再重命名；Windows 文件名不允许冒号，时间部分用 HHMMSS。
    """

    PRESETS = {
        '文件日期':  {'prefix': '', 'start': 1, 'digits': 3, 'date': False, 'time': True},
        '1001起序':  {'prefix': '', 'start': 1001, 'digits': 4, 'date': False, 'time': False},
        '0001起序':  {'prefix': '', 'start': 1, 'digits': 4, 'date': False, 'time': False},
        '1起序':     {'prefix': '', 'start': 1, 'digits': 0, 'date': False, 'time': False},
        '日期+序号': {'prefix': '', 'start': 1, 'digits': 3, 'date': True, 'time': False},
        '自定义':    {'prefix': '', 'start': 1, 'digits': 3, 'date': False, 'time': False},
    }

    TIME_FORMAT = '%Y%m%d_%H%M%S'  # 20261120_212432
    GUESS_SUFFIX = '_dst'          # 推测时间后缀

    def __init__(self, preset='1001起序', prefix='', start=1, digits=3, date=False, time=False):
        self.preset = preset
        self.prefix = prefix
        self.start = start
        self.digits = digits
        self.date = date
        self.time = time

    @classmethod
    def from_preset(cls, preset, prefix='', start=1, digits=3):
        p = cls.PRESETS.get(preset, cls.PRESETS['1001起序'])
        if preset == '自定义':
            return cls(preset, prefix=prefix, start=start, digits=digits, date=False, time=False)
        return cls(preset, prefix=p['prefix'], start=p['start'], digits=p['digits'],
                   date=p.get('date', False), time=p.get('time', False))

    def format(self, seq, when=None, guessed=False):
        """生成基础名（不含扩展名）。

        时间方案用 ``when``（媒体时间）命名，``guessed=True`` 时追加 ``_dst``；
        其余方案仍按序号 ``seq`` 命名。
        """
        if self.time:
            when = when or datetime.datetime.now()
            base = when.strftime(self.TIME_FORMAT)
            return f"{base}{self.GUESS_SUFFIX}" if guessed else base
        if self.date:
            d = datetime.datetime.now().strftime('%Y%m%d')
            if self.prefix or (self.digits and self.digits > 0):
                return f"{d}_{self.prefix}{seq:0{self.digits}d}"
            return f"{d}_{seq:03d}"
        if self.digits and self.digits > 0:
            return f"{self.prefix}{seq:0{self.digits}d}"
        return f"{self.prefix}{seq}"

    def preview(self, count=3):
        """预览前几张的命名，用于 UI 展示；时间方案展示真实/推测两种写法。"""
        if self.time:
            now = datetime.datetime.now()
            samples = [
                self.format(self.start, when=now),
                self.format(self.start, when=now, guessed=True),
            ]
            return samples[:max(1, count)]
        return [self.format(self.start + i) for i in range(count)]


def unique_path(folder, base, ext):
    """返回不覆盖已有文件的完整路径；重名时依次追加 ``_2``、``_3`` …"""
    candidate = os.path.join(folder, f"{base}{ext}")
    n = 2
    while os.path.exists(candidate):
        candidate = os.path.join(folder, f"{base}_{n}{ext}")
        n += 1
    return candidate


def compute_start(folder, scheme):
    """扫描文件夹，返回不覆盖已有文件的实际起始序号（>= 用户设定 start）。

    ``文件日期`` 按时间命名、与序号无关，直接返回起始序号，重名由
    :func:`unique_path` 兜底。
    """
    if scheme.time or not os.path.isdir(folder):
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
