# -*- coding: utf-8 -*-
"""微信图片下载工具 - 配置"""

import os

# GUI 外观配置
GUI_CONF = {
    'window_title': '微信图片下载工具',
    'window_geometry': '820x780',
    'window_resizable': True,
    'appearance_mode': 'Light',
    'color_theme': 'blue',
    'log_colors': {
        'info': 'white',
        'success': 'green',
        'warning': 'yellow',
        'error': 'red',
        'input': 'green',
    },
}

# 按钮样式（基于用户 1688 工具的蓝橙配色）
BUTTON_CONF = {
    'width': 110,
    'height': 36,
    'corner_radius': 8,
    'border_width': 0,
    'themes': {
        'default': {
            'primary':   {'fg_color': '#3B82F6', 'hover_color': '#2563EB', 'text_color': 'white'},
            'success':   {'fg_color': '#10B981', 'hover_color': '#059669', 'text_color': 'white'},
            'danger':    {'fg_color': '#EF4444', 'hover_color': '#DC2626', 'text_color': 'white'},
            'warning':   {'fg_color': '#FB923C', 'hover_color': '#F97316', 'text_color': 'white'},
            'secondary': {'fg_color': '#6B7280', 'hover_color': '#4B5563', 'text_color': 'white'},
        },
    },
    'current_theme': 'default',
}


def get_button_style(style_type='primary'):
    theme = BUTTON_CONF['themes'].get(BUTTON_CONF['current_theme'], BUTTON_CONF['themes']['default'])
    return theme.get(style_type, theme['primary'])


def get_button_config(style_type='primary'):
    style = get_button_style(style_type)
    return {
        'width': BUTTON_CONF['width'],
        'height': BUTTON_CONF['height'],
        'corner_radius': BUTTON_CONF['corner_radius'],
        'border_width': BUTTON_CONF['border_width'],
        **style,
    }


def _home_dir():
    """当前用户主目录（不写死用户名，换机器也能用）"""
    try:
        return os.path.expanduser('~')
    except Exception:
        return ''


def default_image_folder():
    """默认保存目录：优先『桌面/图片下载』，没有桌面目录时退回主目录"""
    home = _home_dir()
    desktop = os.path.join(home, 'Desktop')
    base = desktop if os.path.isdir(desktop) else home
    return os.path.join(base, '图片下载')


def default_wechat_src():
    """探测微信默认保存目录，兼容 3.x / 4.x 及自定义安装位置"""
    home = _home_dir()
    candidates = [
        os.path.join(home, 'Documents', 'WeChat Files'),
        os.path.join(home, 'Documents', 'xwechat_files'),
        os.path.join(home, 'Documents', 'WeChat Files', 'xwechat_files'),
        r'C:\WeChat Files',
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    # 都找不到时返回候选路径，供用户手动修改
    return candidates[1]


# 功能默认值
DEFAULTS = {
    'image_folder': default_image_folder(),
    'download_count': 10,
    'wechat_save_src': default_wechat_src(),  # 监控来源（微信默认保存目录）
    'next_key': 'right',            # 切下一张所用按键
}

# 支持的图片扩展名
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')

# 厘米转磅（Word 单位）系数
CM_TO_PT = 28.35
