# WeChatImageTool · 微信图片批量下载工具

> 一键保存微信聊天图片到本地，自动命名、自动编号、支持窗口选择与多种命名规则。

![GitHub repo size](https://img.shields.io/github/repo-size/lytssaa/WeChatImageTool)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

**关键词**：微信图片下载、微信图片批量保存、WeChatImageDownloader、微信聊天记录图片导出、微信PC图片下载、微信图片自动命名、CustomTkinter、PyInstaller、剪贴板下载、Ctrl+S另存为、微信图片整理工具。

---

## 界面截图

![WeChatImageTool 主界面](assets/screenshot.png)

---

## 功能特性

- **两种下载模式**
  - **剪贴板复制（推荐）**：模拟 `Ctrl + C` 读取微信图片查看器剪贴板内容，直接写入目标文件夹，绕过微信「另存为」对话框。
  - **Ctrl + S 接管**：自动识别微信「另存为」对话框，切换目录、填写文件名、用 `Alt + S` 提交保存；失败时自动从微信默认目录兜底搬移。
- **手动选择微信窗口**：避免工具自身抢焦点导致保存失败。
- **5 种命名方案**：`1001 起序`、`0001 起序`、`1 起序`、`日期 + 序号`、`自定义前缀 / 起始序号 / 位数`。
  - 自动顺延已有编号，避免覆盖旧文件。
- **运行日志可折叠**：日志区支持收起 / 展开，无需拖拽窗口边框。
- **一键清空图片文件夹**：在路径设置右侧直接清空。
- **单文件 exe**：已用 PyInstaller 打包成 `WeChatImageTool.exe`，无需安装 Python 即可运行。

---

## 下载与安装

### 方式一：直接下载 exe（推荐）

从本仓库 [Releases](../../releases) 下载 `WeChatImageTool.exe`，双击运行即可。

> 仓库根目录 `dist/WeChatImageTool.exe` 即为最新构建版本。

### 方式二：源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/lytssaa/WeChatImageTool.git
cd WeChatImageTool

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate    # macOS/Linux

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python main.py
```

---

## 使用步骤

1. **设置图片保存文件夹**：点击「浏览」选择你要保存图片的目录。
2. **选择微信窗口**：点击「选择微信窗口」，从列表里选中微信图片查看器窗口（通常是「图片和视频」或聊天窗口）。
3. **配置下载参数**：下载数量、命名规则、下载方式。
4. **点击「开始下载」**：3 秒倒计时内，用鼠标点击微信图片查看器窗口使其置顶并保持焦点。
5. **工具自动逐张保存**，日志区实时显示进度。

> **提示**：日常推荐「剪贴板复制」模式，最稳定；「Ctrl + S」模式用于兼容旧版微信或剪贴板失效的场景。

---

## 核心原理

### 剪贴板复制模式

1. 用 `pywin32` 将微信图片查看器窗口置顶。
2. 发送 `Ctrl + C` 把当前图片复制到系统剪贴板。
3. 调用 `PIL.ImageGrab.grabclipboard()` 读取位图；如果微信复制的是文件路径，则读取 `CF_HDROP` 列表。
4. 保存到目标文件夹，并按命名规则重命名。
5. 按 `→`（右方向键）切换到下一张，循环执行。

为了应对「切图后图片还没渲染完」的偶发竞态，单张图内部会**周期性重发 Ctrl + C 并轮询剪贴板**（最多 4 次，约 8 秒），只有真正抓不到才跳过继续。

### Ctrl + S 接管模式

1. 发送 `Ctrl + S` 调出微信「另存为」对话框。
2. 枚举类名为 `#32770` 的对话框，结合标题/控件启发式定位保存窗口。
3. 用 `Ctrl + L` 聚焦地址栏，粘贴目标文件夹路径并回车，**先把对话框当前目录切过去**。
4. 在文件名框只填 `1001.jpg` 这类 basename，再用 `Alt + S` 提交。
5. 如果对话框检测失败，启动兜底扫描：递归遍历 `WeChat Files` 下最近 15 秒修改过的图片文件，自动搬移到目标文件夹并重命名。

> 所有路径/文件名都通过**剪贴板粘贴**写入，避免中文输入法下 `pyautogui.typewrite` 把 `\` 变成 `、`、数字缺失、中文乱码的问题。

---

## 项目结构

```
WeChatImageTool/
├── assets/
│   └── screenshot.png            # 项目截图
├── core/
│   ├── __init__.py
│   ├── downloader.py             # 下载核心：剪贴板/Ctrl+S/兜底搬移
│   ├── file_ops.py               # 文件夹创建、清空、索引计算
│   └── naming.py                 # 命名规则与起始编号防覆盖
├── gui/
│   ├── __init__.py
│   ├── app.py                    # 主界面与交互逻辑
│   ├── logging.py                # 日志着色输出
│   ├── utils.py                  # 通用 UI 工具函数
│   └── widgets.py                # 自定义卡片、文本框等控件
├── .gitignore
├── build.bat                     # Windows 一键打包脚本
├── config.py                     # 默认配置（路径、窗口大小等）
├── diag_dialog.py                # 调试：枚举保存对话框信息
├── dist/
│   └── WeChatImageTool.exe       # 打包后的单文件可执行程序
├── main.py                       # 入口文件
├── README.md                     # 本文件
└── requirements.txt              # Python 依赖
```

---

## 依赖

```
customtkinter>=6.0.0
Pillow>=10.0.0
pyautogui>=0.9.54
pywin32>=306
```

详见 [`requirements.txt`](requirements.txt)。

---

## 打包 exe

```bash
# 在 Windows 下执行（已包含在 build.bat 中）
python -m PyInstaller --noconfirm --onefile --windowed \
  --name WeChatImageTool \
  --collect-all customtkinter \
  --hidden-import win32com \
  --hidden-import pywin32 \
  --hidden-import pyautogui \
  --hidden-import win32clipboard \
  --hidden-import PIL.ImageGrab \
  main.py
```

打包产物位于 `dist/WeChatImageTool.exe`。

---

## 常见问题

**Q：点开始下载后保存 0 张？**  
A：请确保在倒计时结束前，用鼠标点击微信图片查看器窗口使其保持前台焦点。建议先点「选择微信窗口」手动指定。

**Q：Ctrl + S 模式保存到了其他目录？**  
A：工具会先尝试把「另存为」对话框切到目标文件夹再保存。如果微信版本特殊导致接管失败，会兜底从微信默认目录把最新图片搬过去。

**Q：日志区看不到/被挤没？**  
A：当前版本已把日志区用固定高度容器包裹，并支持「收起日志 / 展开日志」按钮。

**Q：某些图一直跳过？**  
A：动图、视频、表情包或需要点「查看原图」的大图可能无法通过 `Ctrl + C` 抓取，属于正常跳过。

---

## 免责声明

本工具仅用于**个人备份自己微信聊天记录中的图片**，请遵守相关法律法规与微信用户协议，不得用于爬取他人数据、批量下载非授权内容或任何违法用途。

---

## License

[MIT](LICENSE)
