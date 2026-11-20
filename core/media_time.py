# -*- coding: utf-8 -*-
"""媒体时间处理：给下载后的图片/视频写入「拍摄/消息时间」。

微信转发会抹掉标准 EXIF，落盘图片还是加密的 ``.dat``；但实测仍有多条可用的
时间证据链（按可信度排序）：

  1. **EXIF 拍摄时间**：点「查看原图」时微信会把原图解码到
     ``temp\\RWTemp\\YYYY-MM\\<hash>.jpg``，原片（如小米）的 EXIF 日期串
     仍保留在字节里，可直接扫描出来，这是真实拍摄时间；
  2. **微信消息时间（估算）**：图片解码/复制时会读取对应 ``.dat``，把访问时间
     更新为当前；据此定位到具体那张，再取同一消息 ``.dat / _h / _W / _t / _t_W``
     中最早的文件时间（缩略图通常随消息接收就落盘，最接近发送时间）；视频取
     落盘 mp4 的创建/修改时间；
  3. 源文件创建/修改时间（仅非临时目录的文件有效）；
  4. 非临时路径里的 ``YYYY-MM`` 月份推测（取该月 15 日 12:00；微信临时目录的
     月份是“解码当月”，不可用）；
  5. 当前时间（下载时间）兜底。

选定后写入目标文件的修改时间与 Windows 创建时间，资源管理器、相册、
按时间排序都能得到接近真实的时间。
"""

import hashlib
import os
import re
import time
from datetime import datetime

YearMonthRe = re.compile(r'(?<!\d)(20\d{2})[-_/]?(0[1-9]|1[0-2])(?!\d)')
# EXIF 标准日期字符串：2026:11:18 15:11:56
ExifDateRe = re.compile(
    rb'(20\d{2}):(0[1-9]|1[0-2]):(0[1-9]|[12]\d|3[01]) '
    rb'([01]\d|2[0-3]):([0-5]\d):([0-5]\d)'
)


def _valid(dt):
    return isinstance(dt, datetime)


# 只有图片才值得扫 EXIF（避免误扫视频大文件）
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tif', '.tiff', '.heic')


def is_image_path(path):
    return bool(path) and os.path.splitext(path)[1].lower() in IMAGE_EXTS


def is_transient_source(path):
    """是否是微信临时解码目录里的文件（``temp\\RWTemp``）。

    这类文件的创建/修改时间是「解码那一刻」，不是消息时间，不能直接采用。
    """
    if not path:
        return False
    p = os.path.normpath(path).lower()
    return '\\temp\\' in p or '\\rwtemp\\' in p


def month_from_path(path):
    """从路径里的 ``YYYY-MM`` 取出月份字符串 ``'2026-11'``；失败返回 None。"""
    if not path:
        return None
    match = YearMonthRe.search(path.replace('\\', '/'))
    if not match:
        return None
    return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"


def wechat_root_from_path(path):
    """从微信落盘路径推断微信账号根目录。

    ``...\\xwechat_files\\<账号>\\temp\\RWTemp\\...`` -> ``...\\xwechat_files\\<账号>``
    ``...\\xwechat_files\\<账号>\\msg\\video\\...``      -> ``...\\xwechat_files\\<账号>``
    兼容旧版 ``WeChat Files``。失败返回 None。
    """
    if not path:
        return None
    p = os.path.normpath(path)
    low = p.lower()
    for marker in ('\\temp\\', '\\msg\\'):
        idx = low.find(marker)
        if idx > 0:
            return p[:idx]
    return None


def find_account_root(wechat_src, chat_id):
    """在微信保存根目录下找到含该会话 attach 目录的账号根目录。

    ``wechat_src`` 可能是 ``xwechat_files``（下含账号子目录），也可能本身就是
    账号根目录。找不到返回 None。
    """
    if not wechat_src or not chat_id:
        return None
    md5 = hashlib.md5(chat_id.encode('utf-8')).hexdigest()
    candidates = [wechat_src]
    try:
        for name in os.listdir(wechat_src):
            sub = os.path.join(wechat_src, name)
            if os.path.isdir(sub):
                candidates.append(sub)
    except OSError:
        pass
    for root in candidates:
        if os.path.isdir(os.path.join(root, 'msg', 'attach', md5)):
            return root
    return None


def exif_datetime(path, max_bytes=64 * 1024 * 1024):
    """扫描图片字节里的 EXIF 日期字符串，返回最早的合理时间（拍摄时间）。

    微信转发的压缩图会抹掉 EXIF，此时返回 None。原图（如小米原片）即使
    PIL 解析不到，原始字节里仍保留 ``2000:01:01 00:00:00`` 日期串，可被
    这里直接扫描出来。只在图片上调用，避免误扫视频大文件。
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, 'rb') as f:
            data = f.read(max_bytes)
    except OSError:
        return None
    now = datetime.now()
    found = []
    for m in ExifDateRe.finditer(data):
        try:
            dt = datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)), int(m.group(6)),
            )
        except ValueError:
            continue
        if 1990 <= dt.year <= now.year + 1:
            found.append(dt)
    if not found:
        return None
    # 拍摄时间通常是出现的最早时间（修改时间更晚）
    return min(found)


_THUMB_SUFFIXES = ('_t_W', '_t')
_DAT_SUFFIXES = ('_t_W', '_t', '_h', '_W')


def _dat_hash(name):
    """``58bd..._t_W.dat`` -> ``58bd...``（去掉缩略图/原图/宽图后缀）"""
    low = name.lower()
    if not low.endswith('.dat'):
        return ''
    base = name[:-4]
    for suffix in _DAT_SUFFIXES:
        if base.endswith(suffix):
            return base[:-len(suffix)]
    return base


def _is_thumb(name):
    low = name.lower()
    return any(low.endswith(s + '.dat') for s in _THUMB_SUFFIXES)


def dat_message_evidence(root, chat_id, month=None, after_ts=None, tolerance=10.0):
    """反查刚复制的图片对应的微信消息时间，返回 ``(datetime, 说明)``。

    原理（实测）：
      * 复制/查看图片时微信会读取对应的 ``.dat``，把访问时间更新为当前；
      * 同一消息的 ``<hash>.dat``（大图）、``_h.dat``（原图）、``_t.dat``
        （缩略图）共享 hash，缩略图在**接收消息时**就落盘，大图可能要到
        「第一次打开」才下载，因此取这一组里**最早的**文件时间最接近消息时间。
      * 一次操作会连带读取相邻几张图，其中**最后被读取的主 .dat** 才是当前
        这张（实测复制发生在预加载之后），据此定位 hash。
    """
    if not root or not chat_id:
        return None, ''
    if after_ts is None:
        after_ts = time.time()
    attach = os.path.join(root, 'msg', 'attach', hashlib.md5(chat_id.encode('utf-8')).hexdigest())
    if not os.path.isdir(attach):
        return None, ''
    if month:
        bases = [os.path.join(attach, month)]
    else:
        try:
            bases = [os.path.join(attach, d) for d in os.listdir(attach)]
        except OSError:
            return None, ''

    lower, upper = after_ts - tolerance, after_ts + 60.0

    def scan(low):
        main = {}    # key -> (atime, path)
        read_t = set()  # 同一时间被读了 _t 的 key（多为预加载的相邻图）
        fallback = None  # 只读到 _t 时的后备
        for base in bases:
            if not os.path.isdir(base):
                continue
            for dirpath, _dirs, filenames in os.walk(base):
                for fn in filenames:
                    if not fn.lower().endswith('.dat'):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if not (low <= st.st_atime <= upper):
                        continue
                    key = _dat_hash(fn)
                    if not key:
                        continue
                    item = (st.st_atime, p, key)
                    if _is_thumb(fn):
                        read_t.add(key)
                        if fallback is None or item[0] > fallback[0]:
                            fallback = item
                    else:
                        if key not in main or item[0] >= main[key][0]:
                            main[key] = (item[0], p)
        # 被复制的那张通常只读主文件；预加载的相邻图会连缩略图一起读
        clean = [(at, p, k) for k, (at, p) in main.items() if k not in read_t]
        pool = clean or [(at, p, k) for k, (at, p) in main.items()]
        best = max(pool, key=lambda x: x[0]) if pool else None
        return best, fallback

    best, fallback = scan(lower)
    loose = False
    if best is None and fallback is None:
        # 文件系统延迟更新访问时间时放宽到 1 小时，仍取“最后被读取”的那张
        best, fallback = scan(after_ts - 3600.0)
        loose = True
    chosen = best or fallback
    if chosen is None:
        return None, ''
    _atime, path, key = chosen
    folder = os.path.dirname(path)
    # 同一 hash 的所有副本：取最早的时间（缩略图最接近接收时间）
    times = []
    try:
        siblings = os.listdir(folder)
    except OSError:
        siblings = []
    for fn in siblings:
        if not fn.lower().endswith('.dat') or _dat_hash(fn) != key:
            continue
        p = os.path.join(folder, fn)
        try:
            st = os.stat(p)
        except OSError:
            continue
        for ts in (st.st_ctime, st.st_mtime):
            try:
                dt = datetime.fromtimestamp(ts)
            except (OverflowError, OSError, ValueError):
                continue
            if 2000 <= dt.year <= datetime.now().year + 1:
                times.append((dt, fn))
    if not times:
        return None, ''
    dt, src = min(times, key=lambda x: x[0])
    if _is_thumb(src):
        kind = '缩略图'
    elif src.endswith('_h.dat'):
        kind = '_h 原图'
    elif src.endswith('_W.dat'):
        kind = '_W 版本'
    else:
        kind = '大图'
    return dt, f"{key[:8]}… {kind}{'·宽松匹配' if loose else ''}"


def dat_message_time(root, chat_id, month=None, after_ts=None, tolerance=10.0):
    """只返回反查到的消息时间（保留的简版接口）。"""
    return dat_message_evidence(root, chat_id, month=month, after_ts=after_ts)[0] or None


def source_time(path):
    """源文件的「消息时间」：取创建时间与修改时间中较早且合理的一个。

    微信落盘时创建时间通常就是收到消息的瞬间；修改时间可能因后续读取略晚。
    取较早值更接近消息时间。失败返回 None。
    """
    if not path or not os.path.exists(path):
        return None
    try:
        st = os.stat(path)
    except OSError:
        return None
    times = []
    for ts in (st.st_ctime, st.st_mtime):
        try:
            dt = datetime.fromtimestamp(ts)
        except (OverflowError, OSError, ValueError):
            continue
        # 早于 2000 年的时间视为无效（微信不可能）
        if dt.year >= 2000:
            times.append(dt)
    return min(times) if times else None


def guess_from_path(path):
    """从路径里的 ``YYYY-MM`` 推测一个时间。

    非临时文件：若文件自身时间落在该月，直接用（通常是消息时间）；否则取该月
    15 日 12:00。微信临时解码目录（``temp\\RWTemp``）的月份是**解码当月**，不是
    消息月份，不能用来推测，返回 None。无法解析返回 None。
    """
    if not path or is_transient_source(path):
        return None
    match = YearMonthRe.search(path.replace('\\', '/'))
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    own = source_time(path)
    if own and own.year == year and own.month == month:
        return own
    try:
        return datetime(year, month, 15, 12, 0, 0)
    except ValueError:
        return None


def resolve_media_time(exif_path=None, message_time=None, source_path=None,
                       fallback_path=None, now=None):
    """按证据链挑选时间，返回 ``(datetime, 来源说明)``。

    优先级：EXIF 拍摄时间 > 微信消息时间 > 源文件时间 > 路径月份推测 > 当前时间。
    """
    if exif_path:
        t = exif_datetime(exif_path)
        if t:
            return t, 'EXIF 拍摄时间'
    if _valid(message_time):
        return message_time, '微信消息时间'
    if source_path and not is_transient_source(source_path):
        t = source_time(source_path)
        if t:
            return t, '源文件时间'
    g = guess_from_path(fallback_path or source_path)
    if g:
        return g, '按月份推测'
    return now or datetime.now(), '下载时间'


def choose_media_time(viewer_time=None, source_path=None, fallback_path=None, now=None):
    """旧版简易选择器（保留兼容）；新代码请用 ``resolve_media_time``。

    参数：
      viewer_time   历史上传入的查看器时间戳（实测不随切图变化，已不用于逐张定时间）
      source_path   源媒体文件路径（用于读文件时间）
      fallback_path 用于解析 YYYY-MM 的路径（通常是源文件或目标路径）
      now           兜底时间（默认当前时间）
    """
    if _valid(viewer_time):
        return viewer_time
    st = source_time(source_path)
    if st:
        return st
    g = guess_from_path(fallback_path or source_path)
    if g:
        return g
    return now or datetime.now()


def _set_windows_creation_time(path, dt):
    """设置 Windows 创建时间；失败静默（不影响主流程）。"""
    try:
        import win32con
        import win32file
        import pywintypes
    except Exception:
        return False
    handle = None
    try:
        handle = win32file.CreateFile(
            path,
            win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL,
            None,
        )
        t = pywintypes.Time(dt)
        # (creation, lastAccess, lastWrite)：只改创建时间，避免覆盖 os.utime 的结果
        win32file.SetFileTime(handle, t, None, None)
        return True
    except Exception:
        return False
    finally:
        if handle is not None:
            try:
                handle.Close()
            except Exception:
                pass


def apply_file_time(path, dt):
    """把修改时间/访问时间/创建时间都设为 dt。成功返回 True。"""
    if not path or not _valid(dt) or not os.path.exists(path):
        return False
    try:
        ts = dt.timestamp()
        os.utime(path, (ts, ts))
    except OSError:
        return False
    _set_windows_creation_time(path, dt)
    return True
