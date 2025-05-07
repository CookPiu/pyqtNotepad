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

## 软件架构

本应用程序采用分层架构模式，旨在实现关注点分离、提高模块化程度和可维护性。主要层次和组件如下：

*   **应用入口 (`main.py`)**: 程序的起点，负责初始化 PyQt6 应用和主窗口。
*   **主窗口 (`src/ui/main/main_window.py`)**: 应用程序的顶层窗口，承载所有UI元素和核心交互逻辑。它协调各个子系统和服务的运作。
*   **UI层 (`src/ui/`)**: 负责用户界面的展示和交互。该层遵循组件化设计思想，具体划分为：
    *   **UI管理器 (`src/ui/components/ui_manager.py`)**: 核心的UI协调者，负责主窗口内各个UI区域（如活动栏、侧边栏、编辑器区域、状态栏、Dock小部件）的初始化、布局和管理。
    *   **UI核心 (`src/ui/core/`)**: 包含UI的基础元素，如自定义基类 (`BaseWidget`, `BaseDialog`)，以及主题管理 (`ThemeManager`)，为整个UI提供一致的外观和行为。
    *   **原子组件 (`src/ui/atomic/`)**: 构成界面的最小、可复用的UI单元。例如文本编辑器 (`text_editor.py`)、HTML编辑器 (`html_editor.py`)、日历控件 (`calendar_widget.py`)、计算器 (`calculator_widget.py`)等。
    *   **复合组件 (`src/ui/composite/`)**: 由多个原子组件或简单组件组合而成，实现更复杂的UI功能块。例如，集成了日历、便签待办和计时器的工具箱 (`CombinedTools`)。
    *   **可停靠组件 (`src/ui/docks/`)**: 实现可停靠的窗口功能，如翻译面板 (`TranslationDock`)。这些通常由UI管理器集成到主窗口的特定区域。
    *   **视图 (`src/ui/views/`)**: 代表特定功能的完整界面或大型UI区域，例如笔记下载器界面 (`note_downloader_view.py`)、PDF预览界面 (`pdf_viewer_view.py`)。
    *   **对话框 (`src/ui/dialogs/`)**: 用于特定交互的弹出窗口，如翻译对话框 (`translation_dialog.py`)。
    *   **UI操作逻辑 (`src/ui/components/`)**: 除了UI管理器，此目录还包含处理特定UI交互逻辑的模块，如文件操作 (`file_operations.py`)、编辑操作 (`edit_operations.py`)等，它们通常与主窗口或特定UI组件紧密协作，由主窗口或UI管理器进行调度。
*   **核心功能层 (`src/core/`)**: 包含应用程序的核心业务逻辑和全局配置。
    *   **应用逻辑 (`src/core/app.py`)**: 实现应用级别的主要功能、状态管理和不同模块间的协调。
    *   **设置管理 (`src/core/settings.py`)**: 负责加载、保存和管理用户偏好设置（如主题、字体、窗口状态等）。
*   **服务层 (`src/services/`)**: 提供具体的后台服务和功能实现，供UI层和核心功能层调用，实现业务逻辑与界面展示的分离。
    *   `file_service.py`: 文件读写、管理等。
    *   `format_service.py`: 文本格式化、代码高亮等。
    *   `text_service.py`: 文本处理、查找替换等。
    *   `translation_service.py`: 文本翻译功能。
*   **工具类 (`src/utils/`)**: 包含通用的辅助函数和类，例如PDF处理工具 (`pdf_utils.py`)。
*   **数据 (`data/`)**: 存储应用程序的持久化数据，如日历事件 (`calendar_events.json`)、API凭证和用户配置等。
*   **资源 (`assets/`)**: 存放静态资源，主要是样式表 (QSS) 文件，用于定义亮色和暗色主题。
*   **笔记下载器子模块 (`note_downloader/`)**: 这是一个相对独立的Python项目，作为子模块集成到主应用中。它有自己的依赖、配置和源代码结构，负责从Moodle等平台自动下载课程资料。主应用通过 `src/ui/views/note_downloader_view.py` 与其交互。

以下是软件架构的简化示意图：

```mermaid
graph TD
    A[main.py 应用入口] --> B(MainWindow 主窗口);

    subgraph src [主应用源码]
        direction TB

        subgraph ui [UI层 src/ui]
            direction LR
            B --> UIManager[UI管理器 ui_manager.py];
            UIManager --> UICore[UI核心 ui/core];
            UIManager --> Atomic[原子组件 ui/atomic];
            UIManager --> Composite[复合组件 ui/composite];
            UIManager --> Docks[可停靠组件 ui/docks];
            UIManager --> Views[视图 ui/views];
            UIManager --> Dialogs[对话框 ui/dialogs];
            B --> UIOps[UI操作逻辑 ui/components]; %% UIOps directly used by MainWindow or coordinated by UIManager
        end

        subgraph core_services [核心与服务层]
            direction LR
            subgraph core [核心功能 src/core]
                B --> AppLogic[应用逻辑 app.py];
                AppLogic --> Settings[设置 settings.py];
            end

            subgraph services [服务层 src/services]
                B --> FileService[文件服务];
                B --> FormatService[格式服务];
                B --> TextService[文本服务];
                B --> TranslationService[翻译服务];
            end
        end

        subgraph utils [工具类 src/utils]
            B --> PdfUtils[PDF工具 pdf_utils.py];
        end
    end

    subgraph other [其他模块与数据]
        direction TB
        subgraph data_assets [数据与资源]
            direction LR
            UserData[用户数据 data/] <--> AppLogic;
            Assets[资源 assets/] <--> UICore;
        end

        subgraph note_downloader_module [笔记下载器子模块 note_downloader/]
            NoteDownloaderView[NoteDownloaderView (in src/ui/views)] --> NoteDownloaderCore[note_downloader/src (子模块核心)];
            B --> NoteDownloaderView;
        end
    end

    classDef default fill:#fff,stroke:#333,stroke-width:1px,color:#333;
    classDef entrypoint fill:#f9f,stroke:#333,stroke-width:2px;
    classDef maincomponent fill:#ccf,stroke:#333,stroke-width:2px;
    classDef submodule fill:#lightgrey,stroke:#333,stroke-width:2px;
    classDef datastore fill:#f8c471,stroke:#333,stroke-width:1px;

    class A entrypoint;
    class B,UIManager,AppLogic,FileService,FormatService,TextService,TranslationService,PdfUtils,NoteDownloaderView,UIOps maincomponent;
    class NoteDownloaderCore submodule;
    class UserData,Assets datastore;
```

## 项目结构

```plaintext
pyqtNotepad/
├── .gitattributes
├── .gitignore
├── environment.yml          # Conda 环境文件
├── main.py                  # 应用程序入口点
├── README.md                # 项目说明文档
├── requirements.txt         # Pip 依赖项列表
├── assets/                  # 资源文件夹
│   ├── style.qss            # 主样式文件
│   ├── style_dark.qss       # 暗色主题样式
│   └── style_light.qss      # 亮色主题样式
├── data/                    # 用户数据
│   ├── calendar_events.json # 日历事件存储
│   └── speech_recognition/  # 语音识别相关数据
│       └── config.json
├── note_downloader/         # 笔记下载器子模块 (独立项目)
│   ├── environment.yml
│   ├── README.md
│   ├── config/
│   │   ├── classify_rules.yaml
│   │   └── config.yaml
│   ├── downloads/
│   │   └── ...              # 下载的文件 (结构复杂，省略)
│   └── src/
│       ├── __init__.py
│       ├── checker.py
│       ├── classifier.py
│       ├── crawler.py
│       ├── downloader.py
│       ├── main.py
│       └── utils.py
├── src/                     # 源代码目录
│   ├── __init__.py          # 使 src 成为一个包
│   ├── core/                # 核心功能
│   │   ├── __init__.py
│   │   ├── app.py           # 应用程序核心逻辑
│   │   └── settings.py      # 应用程序设置管理
│   ├── services/            # 服务层
│   │   ├── __init__.py
│   │   ├── file_service.py
│   │   ├── format_service.py
│   │   └── text_service.py
│   ├── ui/                  # 用户界面组件
│   │   ├── __init__.py
│   │   ├── atomic/          # 原子组件 (基础、可复用的小部件)
│   │   │   ├── __init__.py
│   │   │   ├── file_explorer.py # 文件浏览器
│   │   │   ├── calendar/
│   │   │   │   ├── __init__.py
│   │   │   │   └── calendar_widget.py # 日历小部件
│   │   │   ├── editor/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── html_editor.py     # HTML 编辑器
│   │   │   │   ├── resizable_image_text_edit.py # 可调整大小图片的文本编辑器
│   │   │   │   └── text_editor.py     # 纯文本编辑器 (带行号)
│   │   │   └── mini_tools/
│   │   │       ├── __init__.py
│   │   │       ├── calculator_widget.py # 计算器小部件
│   │   │       ├── README_speech_recognition.md # 语音识别模块说明
│   │   │       ├── speech_config.py     # 语音识别配置
│   │   │       ├── speech_recognition_widget.py # 语音识别小部件
│   │   │       └── timer_widget.py    # 计时器小部件
│   │   ├── components/      # UI 组件 (处理特定UI逻辑)
│   │   │   ├── __init__.py
│   │   │   ├── edit_operations.py   # 编辑操作相关逻辑
│   │   │   ├── file_operations.py   # 文件操作相关逻辑
│   │   │   ├── ui_manager.py        # UI 整体管理
│   │   │   └── view_operations.py   # 视图操作相关逻辑
│   │   ├── composite/       # 复合组件 (组合多个组件形成复杂功能单元)
│   │   │   ├── __init__.py
│   │   │   ├── combined_notes.py    # 组合便签和待办的控件
│   │   │   └── combined_tools.py    # ★ 组合日历/便签待办/计时器的分页控件
│   │   ├── core/            # UI 核心 (基础类、主题管理等)
│   │   │   ├── __init__.py
│   │   │   ├── base_dialog.py       # 对话框基类
│   │   │   ├── base_widget.py       # 小部件基类
│   │   │   └── theme_manager.py     # 主题管理
│   │   ├── dialogs/         # 对话框组件
│   │   │   └── __init__.py
│   │   ├── main/            # 主应用界面相关
│   │   │   ├── __init__.py
│   │   │   ├── main_window.py       # 主窗口
│   │   │   └── ui_initializer.py    # UI 初始化器
│   │   └── views/           # 视图层 (顶层窗口或复杂视图的容器)
│   │       ├── __init__.py
│   │       ├── note_downloader_view.py # 笔记下载器界面
│   │       ├── pdf_viewer_view.py    # PDF 预览界面
│   │       ├── sticky_notes_view.py  # 便签视图
│   │       └── todo_list_view.py     # 待办事项视图
│   └── utils/               # 工具类
│       ├── __init__.py
│       └── pdf_utils.py     # PDF处理工具
└── tests/                   # 测试目录
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
