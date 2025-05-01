# 多功能记事本 (PyQt6)

这是一个使用 PyQt6 框架构建的多功能记事本应用程序，旨在提供一个集成化的笔记、工具和文件管理环境。

## 功能特性

*   **编辑器**:
    *   多标签页编辑
    *   文本文件和 HTML 文件读写
    *   PDF 文件预览和转换为可编辑的 HTML
    *   字体和颜色设置
    *   图片插入
    *   查找和替换
*   **工具集**:
    *   **工具箱**: 包含以下分页功能的 Dock 窗口:
        *   **日历**: 查看日历、添加/编辑/删除事件。
        *   **便签与待办**: 集成化的便签和待办事项管理。
        *   **计时器**: 包含倒计时和闹钟功能。
    *   **计算器**: 独立的计算器工具。
    *   **笔记下载器**: 集成外部 `note_downloader` 子模块，用于从 Moodle 等平台自动下载课程资料并分类。
        *   **自动爬取与下载**: 自动识别课程资源并下载文件。
        *   **智能分类**: 根据用户定义的规则 (关键字、文件类型、正则表达式) 将文件整理到指定目录。
        *   **增量更新**: 通过文件内容签名或哈希值检测文件变更，避免重复下载。
        *   **手动登录**: 使用 Selenium 辅助用户手动登录 Moodle，脚本自动接管后续操作。
        *   **独立运行**: 该子模块也是一个独立的 Python 项目，有自己的环境和运行方式 (详见 `note_downloader/README.md`)。
*   **文件管理**:
    *   文件浏览器侧边栏 (可展开/折叠)。
*   **界面**:
    *   亮色/暗色主题切换。
    *   类 VS Code 布局 (Activity Bar, Sidebar, Editor Area, Status Bar)。
    *   Zen Mode (F11) 隐藏非必要界面元素。

## 项目结构

```plaintext
pyqtNotepad/
├── main.py                  # 应用程序入口点
├── environment.yml          # Conda 环境文件 (如果使用)
├── requirements.txt         # Pip 依赖项列表
├── README.md                # 项目说明文档
├── assets/                  # 资源文件夹
│   ├── style_light.qss      # 亮色主题样式 (替代 style.qss)
│   └── style_dark.qss       # 暗色主题样式
├── data/                    # 用户数据
│   └── calendar_events.json # 日历事件存储
├── note_downloader/         # 笔记下载器子模块 (独立项目)
│   └── ...
├── src/                     # 源代码目录
│   ├── __init__.py          # 使 src 成为一个包
│   ├── core/                # 核心功能 (待完善)
│   │   ├── __init__.py
│   │   ├── app.py           # (可能已合并到 main.py 或 MainWindow)
│   │   └── settings.py      # 应用程序设置管理 (待实现)
│   ├── services/            # 服务层 (待进一步重构逻辑)
│   │   ├── __init__.py
│   │   ├── file_service.py
│   │   ├── format_service.py
│   │   └── text_service.py
│   ├── ui/                  # 用户界面组件
│   │   ├── __init__.py
│   │   ├── main_window.py   # 主窗口
│   │   ├── editor.py        # 文本编辑器组件 (带行号)
│   │   ├── file_explorer.py # 文件浏览器
│   │   ├── pdf_viewer.py    # PDF预览对话框
│   │   ├── calculator_widget.py # 计算器窗口
│   │   ├── calendar_widget.py # 日历窗口 (现在作为 CombinedToolsWidget 的一部分)
│   │   ├── timer_widget.py    # 计时器窗口 (现在作为 CombinedToolsWidget 的一部分)
│   │   ├── sticky_note_widget.py # 便签组件 (用于 CombinedNotesWidget)
│   │   ├── todo_widget.py     # 待办事项组件 (用于 CombinedNotesWidget)
│   │   ├── combined_notes_widget.py # 组合便签和待办的控件
│   │   ├── combined_tools_widget.py # ★ 组合日历/便签待办/计时器的分页控件
│   │   ├── note_downloader_widget.py # 笔记下载器界面包装器
│   │   └── dialogs/         # 对话框组件
│   │       ├── __init__.py
│   │       └── # (当前对话框在对应 Widget 或 MainWindow 中实现)
│   └── utils/               # 工具类
│       ├── __init__.py
│       ├── pdf_utils.py     # PDF处理工具
│       └── theme_manager.py # 主题管理
└── tests/                   # 测试目录 (待添加)
    └── __init__.py
```

## 安装与运行

1.  **克隆仓库** (如果适用)
    ```bash
    git clone <repository_url>
    cd pyqtNotepad
    ```
2.  **创建虚拟环境** (推荐)
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
    或者使用 Conda:
    ```bash
    conda env create -f environment.yml
    conda activate pynote_env
    ```
3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```
    主要依赖包括 `PyQt6`, `PyQt6-WebEngine`, `PyMuPDF`。
4.  **运行应用程序**
    从项目根目录运行:
    ```bash
    python main.py
    ```

## 后续开发建议

*   将 `MainWindow` 中的文件、格式化、查找替换等逻辑进一步重构到 `core` 或 `services` 中。
*   实现 `core/settings.py` 来持久化用户偏好（如主题、窗口布局、字体大小等）。
*   将常用的对话框（如查找、替换、事件编辑）封装到 `src/ui/dialogs/` 中。
*   优化 PDF 转 HTML 的性能和格式保真度。
*   添加国际化支持。
*   添加单元测试和集成测试到 `tests/` 目录。
*   完善错误处理和用户反馈。
