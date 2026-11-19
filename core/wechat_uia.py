# -*- coding: utf-8 -*-
"""读取微信 4.x 的会话信息（图片查看器 -> 会话 ID -> 当前会话名）。

微信 4.x 的 Qt 界面在 UI Automation 树里暴露了两条关键信息：
  1. 图片查看器根节点的 AutomationId 形如
     ``PreviewWindow_58144075979@chatroom_1794731750_25_0_0``
     其中第二段是会话 ID（群聊以 ``@chatroom`` 结尾）。
  2. 主窗口的聊天输入框 ``chat_input_field`` 的 Name 是当前打开的会话名。

本模块只做只读查询，不修改微信状态。uiautomation 采用延迟导入，
未安装或读取失败时返回 None，调用方可以安全回退到原目录。
"""

import re
import threading

import win32gui
import win32process

_uia = None
_uia_failed = False
_thread_state = threading.local()
_cache_lock = threading.Lock()
_name_cache = {}  # chat_id -> 会话显示名，只在查看器出现瞬间写入
_seen_viewers = {}  # viewer_hwnd -> (chat_id, captured_ok)
_watcher_stop = None
_watcher_thread = None
_watcher_log = None

_INVALID_CHARS = set('<>:"/\\|?*')
_RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    *[f'COM{i}' for i in range(1, 10)],
    *[f'LPT{i}' for i in range(1, 10)],
}


def _load_uia():
    """延迟导入 uiautomation（不在模块加载时引入 comtypes）"""
    global _uia, _uia_failed
    if _uia is not None:
        return _uia
    if _uia_failed:
        return None
    try:
        import uiautomation as auto
        auto.SetGlobalSearchTimeout(2.0)
        _uia = auto
    except Exception:
        _uia_failed = True
        _uia = None
    return _uia


def _ensure_thread(auto):
    """UIA 的 COM 对象必须在创建它的线程里使用，每个线程初始化一次"""
    if not getattr(_thread_state, 'inited', False):
        auto.InitializeUIAutomationInCurrentThread()
        _thread_state.inited = True


def parse_viewer_chat_id(automation_id):
    """从查看器 AutomationId 里提取会话 ID；解析失败返回空字符串"""
    if not automation_id:
        return ''
    match = re.match(r'^PreviewWindow_(.+)_\d+_\d+_\d+_\d+$', automation_id)
    if match:
        return match.group(1)
    if automation_id.startswith('PreviewWindow_'):
        return automation_id[len('PreviewWindow_'):]
    return ''


def sanitize_folder_name(name, max_len=60):
    """把会话名转换为合法的 Windows 文件夹名；无法转换时返回空字符串"""
    if not name:
        return ''
    chars = []
    for ch in name:
        if ch in _INVALID_CHARS or ord(ch) < 32:
            chars.append('_')
        else:
            chars.append(ch)
    safe = re.sub(r'\s+', ' ', ''.join(chars)).strip().rstrip('. ')
    if not safe:
        return ''
    if safe.upper().split('.')[0] in _RESERVED_NAMES:
        safe = '_' + safe
    safe = safe[:max_len].rstrip('. ')
    return safe


def _find_window_by_pid(pid, title=None, require_visible=True):
    """查找指定进程的顶层窗口（可按标题过滤）"""
    found = []

    def callback(hwnd, _):
        try:
            if require_visible and not win32gui.IsWindowVisible(hwnd):
                return True
            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
            if win_pid != pid:
                return True
            if title is not None and win32gui.GetWindowText(hwnd) != title:
                return True
            found.append(hwnd)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(callback, None)
    return found


def find_all_viewer_windows(pid=None):
    """返回所有微信「图片和视频」查看器窗口句柄"""
    found = []

    def callback(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.GetWindowText(hwnd) != '图片和视频':
                return True
            if pid:
                _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
                if win_pid != pid:
                    return True
            found.append(hwnd)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(callback, None)
    return found


def find_viewer_window(pid=None):
    """查找微信「图片和视频」查看器窗口；pid 为空时搜索所有进程"""
    if pid:
        windows = _find_window_by_pid(pid, title='图片和视频')
        return windows[0] if windows else None
    windows = find_all_viewer_windows()
    return windows[0] if windows else None


def _read_current_chat_name(auto, main_hwnd):
    """优先读聊天输入框的 Name，失败时读会话列表里选中项的标题"""
    try:
        main = auto.ControlFromHandle(main_hwnd)
    except Exception:
        return ''

    try:
        field = main.Control(searchDepth=25, AutomationId='chat_input_field')
        name = (field.Name or '').strip()
        if name:
            return name
    except Exception:
        pass

    try:
        session_list = main.Control(searchDepth=20, AutomationId='session_list')
        for item in session_list.GetChildren():
            try:
                if item.GetSelectionItemPattern().IsSelected:
                    name = (item.Name or '').split('\n')[0].strip()
                    if name:
                        return name
            except Exception:
                continue
    except Exception:
        pass
    return ''


def _info_from_viewer(auto, viewer_hwnd, read_current=False):
    try:
        viewer = auto.ControlFromHandle(viewer_hwnd)
        chat_id = parse_viewer_chat_id(viewer.AutomationId or '')
    except Exception:
        return None
    if not chat_id:
        return None

    viewer_tid, pid = win32process.GetWindowThreadProcessId(viewer_hwnd)
    main_hwnd = None
    candidates = _find_window_by_pid(pid, title='微信')
    if candidates:
        # 多账号时优先选与查看器同一 UI 线程的主窗口，避免串号
        same_thread = []
        for hwnd in candidates:
            try:
                if win32process.GetWindowThreadProcessId(hwnd)[0] == viewer_tid:
                    same_thread.append(hwnd)
            except Exception:
                continue
        main_hwnd = (same_thread or candidates)[0]
    if not main_hwnd:
        # 标题可能变化，退化为同进程内类名匹配
        for hwnd in _find_window_by_pid(pid):
            try:
                if auto.ControlFromHandle(hwnd).ClassName == 'mmui::MainWindow':
                    main_hwnd = hwnd
                    break
            except Exception:
                continue

    with _cache_lock:
        name = _name_cache.get(chat_id, '')
    # 只有查看器刚出现时（read_current=True）才允许用主窗口当前聊天名写入缓存，
    # 下载/选窗口时只读缓存，避免用户切换聊天后把当前聊天名误当成图片所属群名。
    if not name and read_current and main_hwnd:
        name = _read_current_chat_name(auto, main_hwnd)
        if name:
            with _cache_lock:
                _name_cache[chat_id] = name

    return {
        'chat_id': chat_id,
        'name': name,
        'is_group': chat_id.endswith('@chatroom'),
        'viewer_hwnd': viewer_hwnd,
    }


def get_chat_info(hwnd, read_current=False):
    """根据窗口句柄读取会话信息。

    ``read_current=True`` 时允许读取主窗口当前聊天名并写入缓存，仅供查看器
    出现瞬间的后台捕获使用；普通调用只读缓存，避免名称漂移。
    返回 ``{'chat_id', 'name', 'is_group', 'viewer_hwnd'}``，失败返回 None。
    如果传入的不是查看器窗口，会自动在同一微信进程里寻找查看器。
    """
    auto = _load_uia()
    if auto is None or not hwnd:
        return None

    try:
        _ensure_thread(auto)
    except Exception:
        return None

    info = _info_from_viewer(auto, hwnd, read_current=read_current)
    if info:
        return info

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return None
    viewer_hwnd = find_viewer_window(pid)
    if viewer_hwnd and viewer_hwnd != hwnd:
        try:
            return _info_from_viewer(auto, viewer_hwnd, read_current=read_current)
        except Exception:
            return None
    return None


def capture_viewer_chat_name(hwnd):
    """在查看器刚出现时读取主窗口当前会话名并缓存，返回会话信息"""
    return get_chat_info(hwnd, read_current=True)


def set_watcher_logger(cb):
    """设置后台捕获的日志回调，签名 cb(msg, level)"""
    global _watcher_log
    _watcher_log = cb or (lambda msg, level='warning': None)


def _log_watcher(msg, level='warning'):
    try:
        (_watcher_log or (lambda m, l: None))(msg, level)
    except Exception:
        pass


def _watcher_loop(interval):
    global _seen_viewers
    try:
        startup_viewers = set(find_all_viewer_windows())
    except Exception:
        startup_viewers = set()
    warned = set()
    while not (_watcher_stop and _watcher_stop.wait(interval)):
        try:
            viewers = find_all_viewer_windows()
        except Exception:
            continue

        current = set(viewers)
        for hwnd in list(_seen_viewers):
            if hwnd not in current and not win32gui.IsWindow(hwnd):
                del _seen_viewers[hwnd]

        for hwnd in viewers:
            state = _seen_viewers.get(hwnd)
            if state and state[1]:
                continue
            try:
                info = capture_viewer_chat_name(hwnd)
            except Exception:
                info = None
            chat_id = (info or {}).get('chat_id', '')
            name = (info or {}).get('name', '')
            captured_ok = bool(chat_id and name)
            _seen_viewers[hwnd] = (chat_id, captured_ok)
            if captured_ok and hwnd in startup_viewers and hwnd not in warned:
                warned.add(hwnd)
                _log_watcher(
                    "检测到工具启动前已打开的微信图片查看器；会话名按当前聊天识别，"
                    "如不正确请重新打开该图片后重新下载。",
                    "warning",
                )


def start_viewer_watcher(interval=0.3, log_cb=None):
    """启动后台监视：查看器出现的瞬间记录「会话 ID -> 群名」映射"""
    global _watcher_stop, _watcher_thread
    if log_cb is not None:
        set_watcher_logger(log_cb)
    if _watcher_thread and _watcher_thread.is_alive():
        return
    _watcher_stop = threading.Event()
    _watcher_thread = threading.Thread(
        target=_watcher_loop, args=(interval,),
        daemon=True, name='WeChatViewerWatcher',
    )
    _watcher_thread.start()


def stop_viewer_watcher():
    """停止后台监视（进程退出时也会随守护线程结束）"""
    if _watcher_stop:
        _watcher_stop.set()
