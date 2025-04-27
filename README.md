# 多功能记事本 (PyQt6)

这是一个使用 PyQt6 框架构建的多功能记事本应用程序。

## 功能特性

*   多标签页编辑
*   文本文件和 HTML 文件读写
*   PDF 文件预览和转换为 HTML
*   字体和颜色设置
*   图片插入
*   查找和替换
*   亮色/暗色主题切换
*   文件浏览器侧边栏
*   计时器和闹钟小工具

## 项目结构

```plaintext
pyqtNotepad/
├── main.py                  # 应用程序入口点
├── requirements.txt         # 依赖项列表
├── README.md                # 项目说明文档
├── assets/                  # 资源文件夹
│   ├── icons/               # 图标文件 (待添加)
│   ├── style.qss            # 亮色主题样式
│   └── style_dark.qss       # 暗色主题样式
├── src/                     # 源代码目录
│   ├── core/                # 核心功能
│   │   ├── __init__.py
│   │   ├── app.py           # 应用程序初始化
│   │   └── settings.py      # 应用程序设置管理 (待实现)
│   ├── ui/                  # 用户界面组件
│   │   ├── __init__.py
│   │   ├── main_window.py   # 主窗口
│   │   ├── editor.py        # 文本编辑器组件
│   │   ├── file_explorer.py # 文件浏览器
│   │   ├── pdf_viewer.py    # PDF查看器
│   │   ├── timer_widget.py  # 计时器组件
│   │   └── dialogs/         # 对话框组件 (待添加)
│   │       ├── __init__.py
│   │       └── about_dialog.py # (示例, 当前实现在 MainWindow)
│   ├── utils/               # 工具类
│   │   ├── __init__.py
│   │   ├── file_utils.py    # 文件操作工具 (待实现)
│   │   ├── pdf_utils.py     # PDF处理工具
│   │   └── theme_manager.py # 主题管理
│   └── services/            # 服务层 (待进一步重构逻辑)
│       ├── __init__.py
│       ├── file_service.py  # 文件操作服务
│       ├── format_service.py # 格式化服务
│       └── text_service.py  # 文本处理服务
└── tests/                   # 测试目录 (待添加)
    └── __init__.py
```

## 安装与运行

1.  **克隆仓库** (如果适用)
    ```bash
    git clone <repository_url>
    cd pyqtNotepad-main
    ```
2.  **创建虚拟环境** (推荐)
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```
3.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```
    *注意：如果缺少图标或其他资源，程序可能无法完全正常运行。*
4.  **运行应用程序**
    ```bash
    python main.py
    ```

## 后续开发建议

*   将 `MainWindow` 中的文件、格式化、文本操作逻辑完全迁移到对应的 `Service` 类中。
*   实现 `core/settings.py` 来保存用户偏好（如主题、窗口大小等）。
*   将 "关于" 对话框实现为 `src/ui/dialogs/about_dialog.py`。
*   在 `assets/icons/` 目录下添加必要的图标文件，并在代码中正确引用。
*   实现 `utils/file_utils.py` 中的文件类型检测等功能。
*   添加单元测试和集成测试到 `tests/` 目录。
*   完善侧边栏其他功能（待办事项、便签等）。
