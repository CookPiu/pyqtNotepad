# 多功能记事本 (PyQt6) 项目文档

这是一个基于 **PyQt6** 框架构建的多功能记事本应用，集成了文本/HTML编辑、PDF预览、日历、便签、待办事项、计时器、计算器以及笔记下载等工具于一体，提供类似 VS Code 的界面布局和丰富的笔记管理功能。本文档详细介绍项目的功能特性、架构设计、源代码结构、主要组件的作用，以及模块间的交互关系，并给出性能优化和改进建议，最后说明运行环境和使用方法，方便维护者理解和使用本项目。

## 功能特性

* **编辑器功能**：支持多标签页文本编辑，可读取和保存纯文本（.txt）、Markdown（.md）、HTML（.html）等文件。提供基础的编辑操作（撤销/重做、剪切复制粘贴）、字体样式和颜色设置、图片插入，以及查找替换功能。同时支持 PDF 文件预览，并可将 PDF 转换为可编辑的 HTML 文件。

* **工具箱**：应用集成一个侧边栏工具箱（Dock 窗口），包含以下分页工具：

  * **日历**：提供月视图日历，可添加、编辑和删除事件（事件持久化存储于 `data/calendar_events.json`）。
  * **便签**：桌面便签和待办事项管理。便签支持多条独立便签笔记（可单独弹出窗口），待办事项支持添加/勾选任务。
  * **待办事项**：与便签在同一分页，通过标签页切换（详见下文 *CombinedNotes* 组件）。
  * **计时器**：倒计时和闹钟工具，可设定定时提醒。
  * **语音识别**：语音转文字工具，支持简单的语音识别和结果插入（需配置 `speech_recognition`，配置文件位于 `data/speech_recognition/config.json`）。

* **独立小工具**：除了上述集成在工具箱内的功能，还有独立窗口的小工具：

  * **计算器**：简易计算器。
  * （未来可扩展其他小工具或整合到工具箱分页中。）

* **笔记下载器**：集成了一个 `note_downloader` 子模块，用于从学习平台（如 Moodle）自动下载课程资料。主要功能包括：

  * **自动爬取下载**：通过 Selenium 协助登录后，自动爬取课程资源链接并下载文件。
  * **智能分类**：支持根据关键字、文件类型、正则规则对下载文件重命名和分类存放。
  * **增量更新**：通过文件哈希或签名检查更新，避免重复下载。
  * **独立运行**：`note_downloader` 也可作为独立项目运行（详见其自带的 README）。在本应用中，通过界面直接调用其功能，日志输出和下载进度会显示在 UI 中。

* **文件管理**：提供侧边栏文件浏览器，可以浏览本地文件系统、选择工作区文件夹、双击打开文件等。文件树支持右键菜单进行重命名、删除等操作。

* **用户界面**：采用类似 VS Code 的多栏布局，包括顶部工具栏、左侧活动栏（切换各模块视图）、侧边栏（文件浏览器/工具箱/下载器等Dock）、主编辑区、下方状态栏等。支持**亮色/暗色主题**一键切换，所有组件会同步更新样式。提供**专注模式（Zen Mode）**：按下 <kbd>F11</kbd> 可切换隐藏菜单栏和工具栏，仅保留主要编辑区域。

## 软件架构

本项目采用分层架构和组件化设计，以实现清晰的模块划分和解耦。主要架构层次和组件如下：

* **应用入口** (`main.py`)：应用程序的启动脚本，负责初始化 PyQt 应用、加载全局设置并创建主窗口实例。

* **主窗口** (`MainWindow` 类，定义于 `src/ui/main/main_window.py`)：应用的核心窗口，承载所有菜单、工具栏、编辑区和Dock组件。`MainWindow` 内聚了文件操作、编辑操作、视图管理等逻辑，通过组合各模块（UI管理器、操作类等）提供整体功能。

* **UI 初始化器** (`UIInitializer` 类，`src/ui/main/ui_initializer.py`)：用于构建主窗口的界面布局和初始化核心视图组件。它负责创建菜单栏、状态栏，设置主布局（左侧文件树 + 右侧编辑区的分割窗口）并将文件浏览器、工具箱、笔记下载器等作为 Dock 部件添加到主窗口。还负责在左侧活动栏添加切换各视图的按钮。

* **UI 管理器** (`UIManager` 类，`src/ui/components/ui_manager.py`)：主窗口的UI调度中心，继承自 QObject，用于管理主题应用、编辑器标签页、动态视图加载和Dock交互等。例如：

  * 管理应用主题：持有 `ThemeManager`，提供 `toggle_theme()` 切换主题，调用 `apply_current_theme()` 遍历所有UI组件更新样式。
  * 管理编辑器标签页：维护当前激活的编辑器组，提供在标签页中打开文件、关闭标签等功能。
  * 动态视图管理：通过 `register_view()` 和 `open_view()` 实现对各种视图（如便签视图、待办视图等）的统一注册和按需显示。当在活动栏点击对应按钮时，UIManager 会创建或显示相应的视图Dock。
  * PDF 文件处理：提供 `open_pdf_preview()`，弹出对话框让用户选择直接预览还是转换为HTML。若选择转换，则启动后台线程执行 PDF→HTML 转换，以防界面卡顿。

* **核心功能层** (`src/core/`)：封装与UI无关的应用核心逻辑和全局配置：

  * **App** (`core/app.py`)：应用程序核心逻辑，例如初始化配置、管理全局状态等（当前主要由 MainWindow 直接处理，后续可迁移部分功能至此）。
  * **设置** (`core/settings.py`)：用户偏好设置的加载与保存，如主题选择、窗口尺寸、最近打开文件等。当前项目中可能是预留模块，实际实现仍有限。

* **服务层** (`src/services/`)：提供独立的业务功能服务，供UI或核心层调用，以实现逻辑与界面的解耦。例如：

  * `file_service.py`：文件读写相关服务，如读取文本文件内容、保存文件等。
  * `format_service.py`：文本格式转换或代码高亮等功能服务。
  * `text_service.py`：文本处理服务，如查找替换实现等。
  * （**注意**：某些服务功能在当前版本中直接在 UI 操作类中实现，`services` 模块有待进一步充实。）

* **工具层 (Utils)** (`src/utils/`)：封装通用的工具函数或类。例如 `pdf_utils.py` 提供PDF转HTML所需的调用（基于 pdf2htmlEX）。

* **UI 层** (`src/ui/`)：包含界面展示和交互逻辑的各组件，进一步细分为多个子层级：

  * **UI原子组件** (`ui/atomic/`)：最基本的界面元素类，通常直接继承自 QtWidgets，例如：

    * `file_explorer.py`：文件浏览器面板，内部使用 `QFileSystemModel + QTreeView` 实现文件树，双击文件发出 `file_double_clicked` 信号供主窗口打开文件。
    * `calendar_widget.py`：日历小部件，实现日历视图和事件管理。
    * 文本编辑器相关：`text_editor.py` 实现纯文本代码编辑器（带行号显示），`html_editor.py` 实现HTML源码编辑器，`resizable_image_text_edit.py` 扩展 QTextEdit 实现富文本和可调整图片插入。
    * `mini_tools/` 子目录：内含各迷你工具部件，例如 `calculator_widget.py` 计算器、`timer_widget.py` 计时器、`speech_recognition_widget.py` 语音识别输入等。
  * **UI复合组件** (`ui/composite/`)：将多个原子组件组合形成更复杂的功能块：

    * `CombinedNotes` (`combined_notes.py`)：便签和待办事项的组合部件。内部使用 `QTabWidget` 实现两个标签页，分别嵌入 `StickyNotesView`（便签视图）和 `TodoListView`（待办视图）。这样用户可以在一个窗口中管理便签和待办，在不同页签来回切换。
    * `CombinedTools` (`combined_tools.py`)：**★ 多屏分页控件**，将日历、便签&待办、计时器、计算器、语音识别等多个工具组合在一个 QTabWidget 中。它作为整个“小工具集合”Dock 的主组件，提供统一的分页界面，便于在一个面板内浏览各种工具。
  * **UI核心组件** (`ui/core/`)：提供UI层的基础支持类：

    * `BaseWidget`/`BaseDialog`：自定义的基础 QWidget 和 QDialog，封装了一些通用行为（如统一调用 `_init_ui`, `_connect_signals`, `_apply_theme` 等模板方法）。
    * `ThemeManager`：主题管理器，加载应用的 QSS 样式表（亮色/暗色）并提供当前主题状态，供 UIManager 调用来应用全局样式。
    * `PanelWidget`：通用面板容器（带标题栏和关闭按钮），用于包装内容组件作为可关闭的Dock面板（例如笔记下载器面板使用 PanelWidget 包裹其内容视图）。
  * **UI功能组件** (`ui/components/`)：封装界面上一些特定交互逻辑或操作的模块：

    * `file_operations.py`：文件相关操作逻辑，如新建、打开、保存、关闭编辑器标签等。例如 `open_file_from_path()` 根据文件类型选择合适的方式打开：文本文件在文本编辑器中打开，图片文件在图像查看器中打开，PDF 文件则调用 UIManager 的 PDF 预览/转换逻辑等。
    * `edit_operations.py`：编辑相关操作逻辑，如撤销/重做、剪切复制、文本格式化等。
    * `view_operations.py`：视图切换及窗口布局相关逻辑，如分屏编辑、全屏模式切换等（目前很多视图操作通过 UIManager 或 MainWindow 直接实现，一些函数可能是预留）。
    * `ui_manager.py`：如前所述，是UI协调管理的核心模块，在此归类为组件便于理解。
  * **UI对话框** (`ui/dialogs/`)：存放各种对话框定义（目前仅包含 PDF 打开时的操作选择对话框 `PdfActionChoiceDialog` 等）。常用对话框如查找/替换、关于窗口等未来可在此扩展。
  * **主界面** (`ui/main/`)：主窗口相关的界面模块：

    * `main_window.py`：主窗口类的具体实现，包括菜单和工具栏创建、信号槽连接（如文件浏览器双击信号连接到打开文件槽等）、以及各核心事件处理（如当前标签变化时更新窗口标题等）。
    * `ui_initializer.py`：UI初始化器，实现主窗口各UI元素的构建和布局（见前述）。
  * **视图层** (`ui/views/`)：以独立窗口或Dock形式呈现的完整界面模块：

    * `note_downloader_view.py`：笔记下载器界面。包含登录指引、开始下载按钮、日志输出区域等，以及内部启动下载线程 (`DownloadWorker`) 执行具体下载逻辑。下载线程结束后通过信号通知UI更新。该视图通常嵌入在 PanelWidget 中作为Dock窗口。
    * `pdf_viewer_view.py`：PDF预览界面。基于 `QWebEngineView` 加载 PDF 文件，提供在应用内预览PDF的功能。
    * `sticky_notes_view.py`：便签视图。显示当前所有便签的列表，并提供新建便签按钮。每个便签以悬浮独立窗口 (`StickyNote` 类) 打开，可拖拽、修改内容和颜色，关闭时通过信号告知视图以更新列表。便签数据持久化保存在 `data/sticky_notes.json`（由 `StickyNoteDataManager` 管理）。
    * `todo_list_view.py`：待办事项视图。以列表形式管理待办任务，支持添加和勾选完成。和便签视图类似，也通过数据文件持久化待办列表。
    * *（其他可能的视图模块如* `office_viewer_view.py` *、* `image_viewer_view.py` *等，按需加载文件时动态创建，这些在文件打开逻辑中使用，并未作为独立菜单/按钮项。）*

下面是项目源代码的简化结构和各文件作用说明：

```plaintext
pyqtNotepad/
├── main.py                  # 应用程序入口点
├── environment.yml          # Conda 环境文件（可选）
├── requirements.txt         # Pip 依赖项列表
├── assets/                  # 前端样式资源
│   ├── style.qss            # 主样式表（包含通用样式）
│   ├── style_dark.qss       # 暗色主题样式
│   └── style_light.qss      # 亮色主题样式
├── data/                    # 用户数据及配置
│   ├── calendar_events.json # 日历事件数据
│   └── speech_recognition/  # 语音识别相关数据
│       └── config.json      # 语音识别配置示例
├── note_downloader/         # 笔记下载器子模块（作为独立项目集成）
│   ├── environment.yml      # 其自身的环境配置
│   ├── README.md            # 其自身的说明文档
│   ├── config/              # 配置文件目录
│   │   ├── classify_rules.yaml
│   │   └── config.yaml
│   ├── downloads/           # 下载结果存放目录
│   │   └── ...              # （结构视下载情况而定）
│   └── src/                 # 子模块源代码
│       ├── checker.py
│       ├── classifier.py
│       ├── crawler.py
│       ├── downloader.py
│       ├── main.py
│       └── utils.py
└── src/                     # 主应用源代码包
    ├── core/                # 核心功能层
    │   ├── app.py           # 应用核心逻辑（预留/待完善）
    │   └── settings.py      # 应用设置管理（预留/待完善）
    ├── services/            # 后端服务层
    │   ├── file_service.py  # 文件读写服务
    │   ├── format_service.py# 文本格式服务
    │   └── text_service.py  # 文本处理服务
    ├── ui/                  # 前端UI层
    │   ├── atomic/          # 原子组件（基础控件）
    │   │   ├── file_explorer.py         # 文件浏览器组件
    │   │   ├── calendar/                
    │   │   │   └── calendar_widget.py   # 日历组件
    │   │   ├── editor/
    │   │   │   ├── html_editor.py       # HTML编辑器
    │   │   │   ├── resizable_image_text_edit.py # 富文本编辑器（支持可调节图片）
    │   │   │   └── text_editor.py       # 纯文本编辑器（带行号）
    │   │   └── mini_tools/             # 迷你工具组件
    │   │       ├── calculator_widget.py # 计算器组件
    │   │       ├── speech_config.py     # 语音识别配置处理
    │   │       ├── speech_recognition_widget.py # 语音识别组件
    │   │       └── timer_widget.py      # 计时器组件
    │   ├── components/      # UI功能组件（封装界面逻辑）
    │   │   ├── edit_operations.py   # 编辑操作逻辑
    │   │   ├── file_operations.py   # 文件操作逻辑
    │   │   ├── ui_manager.py        # UI管理器（主题、视图等）
    │   │   └── view_operations.py   # 视图布局逻辑
    │   ├── composite/       # 复合组件（组合UI单元）
    │   │   ├── combined_notes.py    # 组合便签/待办组件
    │   │   └── combined_tools.py    # 组合多工具的分页组件
    │   ├── core/            # UI基础核心
    │   │   ├── base_dialog.py       # 对话框基类
    │   │   ├── base_widget.py       # 基础Widget类
    │   │   └── theme_manager.py     # 主题管理类
    │   ├── dialogs/         # UI对话框
    │   │   └── pdf_action_dialog.py # PDF打开操作选择对话框
    │   ├── main/            # 主窗口相关模块
    │   │   ├── main_window.py       # 主窗口类定义
    │   │   └── ui_initializer.py    # 界面初始化模块
    │   └── views/           # 视图模块（独立界面）
    │       ├── note_downloader_view.py # 笔记下载器视图
    │       ├── pdf_viewer_view.py    # PDF预览视图
    │       ├── sticky_notes_view.py  # 便签视图
    │       └── todo_list_view.py     # 待办视图
    └── utils/               # 工具模块
        └── pdf_utils.py     # PDF 转换工具函数
```

### 主要类与模块说明

* **MainWindow** (`main_window.py`)：核心主窗口类，继承自 QMainWindow。内部组合了菜单栏、工具栏、状态栏、活动栏按钮和中央编辑区等元素。`MainWindow` 创建时会实例化 `UIManager`、`FileOperations` 等辅助对象并调用 `UIInitializer.setup_ui()` 构建界面。此外还定义了若干槽函数处理用户操作：如 `handle_file_explorer_double_click()` 打开文件，`on_current_tab_changed()` 更新当前编辑器状态，`on_editor_content_changed()` 监测编辑器内容修改以更新窗口标题上的“\*”标记等。

* **UIManager** (`ui_manager.py`)：封装UI全局行为的管理类。如上所述，它负责主题切换、视图Dock管理等。值得注意的是 UIManager 使用 `QThread` 实现了PDF转换的异步处理：通过内部的 `PdfToHtmlWorkerForUIManager` 对象在线程中调用 `pdf_utils.extract_pdf_content()` 完成 PDF→HTML，并用信号通知主线程更新标签页。UIManager 还维护了 `view_instances` 和 `view_docks` 字典，保存已创建的视图对象及对应Dock，以实现再次打开时重用和关闭时同步按钮状态。

* **FileOperations** (`file_operations.py`)：封装文件的新建、打开、保存、关闭等操作。其方法 `open_file_from_path(path)` 会根据文件扩展名选择打开方式：

  * 文本/Markdown：读取文件内容后，在文本编辑器或Markdown编辑器中打开。
  * HTML：读取内容后，使用 `HtmlViewContainer` 容器（内含一个富文本编辑器和预览切换功能）打开，以支持所见即所得的编辑。
  * PDF：调用 `UIManager.open_pdf_preview()` 弹出对话框，由用户选择预览或转换。预览则在新标签中加载 `PdfViewerView`（基于 QWebEngineView 显示PDF）；转换则启动后台线程，待转换完成后，将生成的HTML文件用富文本编辑器打开（HTML源码插入编辑器，允许用户编辑）。
  * 图片/视频：分别使用 `ImageViewWidget` 或 `VideoPlayerWidget` 打开（这些组件在第一次使用时创建）。
  * Office文档：如果在Windows环境，提供转换为PDF或HTML预览的选项，调用 `OfficeViewerWidget` 打开（需要本地Office支持转换）。
    另外，FileOperations 还提供 `new_file()` 方法创建新文件标签页（可选创建文本、HTML或Markdown）；`save_file()`/`save_file_as()` 保存当前文件内容到磁盘；`close_tab()` 关闭标签页等功能。

* **EditOperations** (`edit_operations.py`)：提供编辑菜单相关操作封装。例如 `undo()`/`redo()` 撤销重做、`cut()`/`copy()`/`paste()` 剪切板操作、`select_all()` 全选、`insert_date()` 插入当前日期时间、`toggle_wrap()` 切换自动换行等。这样将编辑动作从界面逻辑中分离，便于在菜单、工具栏或快捷键触发时调用相应函数。

* **视图类**：如 `StickyNotesView` 和 `TodoListView` 均继承自 `BaseWidget`。其中 `StickyNotesView` 内部维护一个 `NotesListWidget` 列表控件列出所有便签摘要，并使用 `StickyNoteDataManager` 处理JSON数据的加载保存。当用户新建便签时，实例化一个 `StickyNote` 窗口（独立的 QWidget，使用 `Qt.Tool` 窗口标志实现在任务栏隐藏、小窗口悬浮）。每个便签窗口关闭时发出自定义信号，将自身ID通知 StickyNotesView，后者据此从列表和数据中移除对应项。**CombinedNotes** 通过同时创建一个 StickyNotesView 和一个 TodoListView 来组合显示，切换标签即可在同一窗口查看便签或待办事项。

* **CombinedTools**：这个类是实现前端**多屏分页**的重要组件。它在初始化时创建了五个子工具组件：计算器、定时器、语音识别、日历，以及 CombinedNotes（便签&待办）。每个组件作为一个标签页添加到其内部的 QTabWidget 中。CombinedTools 继承自 BaseWidget，会随着主题变化调用各子组件的 `update_styles` 方法，确保分页内不同工具的界面风格一致。该组件最终被放入一个 QDockWidget 容器，成为左侧“小工具集合”Dock。当用户点击主窗口活动栏的“小工具”按钮时，如果 Dock 尚未创建，UIInitializer 会创建 CombinedTools 实例并添加到 Dock 显示。

* **NoteDownloader**：笔记下载器作为子模块集成，其主要界面逻辑在 `NoteDownloaderView`。界面由两部分构成：顶部是手动登录和配置区域（如果需要浏览器登录，嵌入 QWebEngineView），底部是日志输出控制台。点击“开始下载”后，会根据配置启动后台 DownloadWorker 线程。DownloadWorker 在自己的 `run()` 方法中调用 note\_downloader 子模块的函数执行下载流程，并通过信号实时发送日志信息。NoteDownloaderView 收到日志信号后，将文本追加到日志窗口显示，方便用户跟踪进度。下载完成或出错时，DownloadWorker 发出 `finished` 信号，视图捕获后可以更新UI状态（例如重新启用“开始下载”按钮等）。通过这种线程机制，耗时的网络下载不会阻塞主界面，提升了应用响应速度。

### 模块间交互关系

各模块之间通过信号和方法调用协同工作，下面列举关键的交互流程：

* **文件打开流程**：用户通过菜单或快捷键触发`打开文件`操作 -> MainWindow 调用 FileOperations.open\_file\_dialog() 弹出 QFileDialog-> 用户选择文件后，FileOperations.open\_file\_from\_path() 分析文件类型并调用相应处理（如文本则创建编辑器标签页，PDF则委托UIManager处理）。如果是通过文件浏览器双击文件，则触发 FileExplorer.file\_double\_clicked 信号，由 MainWindow\.handle\_file\_explorer\_double\_click() 捕获并直接调用 FileOperations.open\_file\_from\_path()。

* **编辑器标签管理**：MainWindow 初始化时通过 UIInitializer 创建 `RootEditorAreaWidget` 作为中央区域。RootEditorAreaWidget 内部维护了一个 `DockableTabWidget`（继承自 QTabWidget）。FileOperations 每次打开文件都会在当前编辑器组的 TabWidget 新增一个标签页并显示。标签页的关闭由 TabWidget 的 tabCloseRequested 信号连接到 FileOperations.close\_tab() 槽处理。currentChanged 信号连接到 MainWindow\.on\_current\_tab\_changed()，以更新当前活动文档和窗口标题。

* **Dock 面板切换**：左侧活动栏的按钮通过 clicked 信号调用 UIInitializer 相应的切换方法。例如“文件”按钮连接 `_toggle_file_explorer_visibility()`，其内部调用 `file_explorer.setVisible(checked)` 显示/隐藏文件浏览器；“小工具”按钮连接 `_toggle_mini_tools_dock()`，首次点击时创建 CombinedTools 和 DockWidget，之后仅设置可见性；“笔记下载器”按钮类似，通过 `_toggle_note_downloader_panel_visibility()` 控制 PanelWidget 的显示。另外，对于动态注册的视图（如便签视图StickyNotes），活动栏按钮的点击采用 UIManager.open\_view 打开Dock。每个Dock的 visibilityChanged 信号都连接到 UIManager.\_handle\_dock\_visibility\_change，用于在Dock被用户关闭时将对应按钮状态置为未选中。

* **主题切换**：用户通过菜单选择切换主题时，调用 UIManager.toggle\_theme() -> 这将切换 ThemeManager 内部保存的主题标志，并调用 apply\_current\_theme()。apply\_current\_theme 遍历所有主要UI组件更新样式：包括为整个应用加载相应的QSS样式表、调整全局字体大小，以及调用每个打开的编辑器和视图的 `update_styles()` 方法。CombinedTools 和 CombinedNotes 的 update\_styles 会进一步调用子组件的更新方法。因此，主题切换可实时反映到所有界面元素上。

## 性能与优化建议

在检查本项目当前实现的基础上，这里总结了一些关于前端多屏分页、组件通信和整体性能的优化建议：

* **优化分页组件的加载**：目前 CombinedTools 在首次创建时会一次性实例化所有分页内的子组件。如果某些子组件初始化较慢（例如语音识别组件可能加载模型或麦克风权限，PDF预览组件加载 WebEngine 等），可能导致打开“小工具”面板时出现短暂卡顿。建议改进为**懒加载**：在用户切换到某个页签时再初始化对应组件。例如 CombinedTools 可以先添加占位页，当用户点击某个标签页时再动态创建相应工具widget并替换占位内容。这样可显著提高首次打开工具面板的响应速度。

* **改进分页切换体验**：针对“多页不连贯”问题，建议在界面切换分页时保持上下文连续性。例如当用户上次关闭应用时工具箱停留在“日历”页签，则下次打开时可以记住并默认显示该页（可将上次活跃索引保存在配置中）。另外，可以在不同分页间共享部分数据：例如**便签**和**待办**虽然分属两个页签，但实际数据相关联时可在切换时自动刷新，确保显示的是最新内容。

* **组件通信与数据同步**：目前便签和待办作为 CombinedNotes 的子视图统一管理，但同时应用还支持通过活动栏分别打开独立的便签视图和待办视图（各自Dock）。需注意避免**数据不同步**：如果用户同时打开了工具箱中的便签页和独立Dock的便签视图，对便签的增删改应该同步更新双方界面。为避免混淆，可以考虑限制便签/待办视图只通过工具箱访问，或确保所有便签操作最终作用于同一个数据源并通知所有视图刷新。类似地，笔记下载器在 PanelWidget Dock 和动态Dock 两种方式只应存在一种，以防止重复实例造成冲突。

* **信号槽连接可靠性**：检查所有信号槽确保正确连接和释放。例如 MainWindow 在重新初始化标签页时重复连接信号需要先断开旧连接，应用关闭时应确保后台线程正常终止（当前 DownloadWorker 在 NoteDownloaderView\.closeEvent 中有安全退出处理）。这些措施在代码中已有所体现，但维护者应在新增功能时保持此惯例，防止出现信号未断开导致的重复执行或内存泄漏。

* **提高文件打开效率**：对于非常大的文本文件，直接在主线程读取并显示可能造成UI短暂无响应。可以考虑在打开大文件时增加进度指示或**后台加载**机制。例如先快速打开一个空编辑器并返回UI响应，然后在单独的线程读取文件内容，读取完成后再将内容填充到编辑器。另外，对于PDF转HTML这样的重度操作，本项目已经使用线程处理；类似思路也可应用到其他潜在耗时任务上。

* **应用启动性能**：应用启动时会初始化一些组件，比如 `NoteDownloaderView` 在 UIInitializer 中提前创建。如果启动速度不理想，可以延迟这些组件的加载到用户实际需要时（比如首次点击相应按钮时再初始化）。同时，尽量减少启动时不必要的资源加载和计算。也可考虑提供**启动欢迎界面**或加载动画，以提升用户感知性能。

上述优化可以提升应用在分页切换时的流畅度和整体响应速度，改善用户体验。后续开发中可逐步验证并应用这些改进。

*(注：以下列出项目中已经规划的进一步开发方向，以供参考：完善设置持久化、增加单元测试、丰富错误处理和用户提示、支持更多语言等。这些也有助于提高应用的健壮性和可维护性。)*

## 安装与运行

按照以下步骤配置运行环境并启动应用：

1. **克隆源码**（或直接下载源码压缩包）：打开终端执行：

   ```bash
   git clone https://github.com/YourUsername/pyqtNotepad.git
   cd pyqtNotepad
   ```

2. **创建虚拟环境**（可选但推荐）：确保已安装 Python 3.9+ 和 pip。然后执行：

   ```bash
   python -m venv venv
   # Windows 下激活虚拟环境：
   venv\Scripts\activate
   # 或 macOS/Linux 下：
   source venv/bin/activate
   ```

   如果使用 Anaconda/Miniconda，也可以通过项目自带的 `environment.yml` 创建环境：

   ```bash
   conda env create -f environment.yml
   conda activate pynote_env
   ```

3. **安装依赖库**：在激活的环境中运行：

   ```bash
   pip install -r requirements.txt
   ```

   主要依赖包括 **PyQt6**, **PyQt6-WebEngine**, **PyMuPDF**, **requests**, **pyyaml**, **speechrecognition** 等。本项目已在 Windows 10 和 Ubuntu 22.04 下测试运行，请确保对应平台能够安装上述依赖。

4. **启动应用程序**：在项目根目录执行：

   ```bash
   python main.py
   ```

   首次运行会打开主窗口（默认浅色主题）。您可以通过“文件”菜单或左侧活动栏按钮来使用各项功能。例如，点击左下角“笔记”按钮打开笔记下载器（首次使用需按照提示登录），点击“工具”按钮展开日历/便签等工具箱。

5. **退出应用**：直接关闭主窗口即可。应用当前版本尚未实现用户设置的持久化保存，后续可能会增加在退出时记忆窗口大小、最近文件等功能。

## 运行环境要求

* Python 版本：3.9 或以上 (支持 PyQt6)
* 操作系统：Windows、macOS 或 Linux 均可。Windows 用户在使用笔记下载器的 Office 转换功能时需安装 Microsoft Office；Linux/macOS 用户因调用限制，该功能不可用，其余功能不受影响。
* 必要依赖：`PyQt6` 图形库，`PyQt6-WebEngine` 用于内嵌浏览器（PDF预览、富文本编辑器等），`PyMuPDF` 用于 PDF 文件解析，`SpeechRecognition` 用于语音识别（需要额外安装语音识别的依赖，如 `pyaudio` 或选择其它STT接口），以及 Selenium 和浏览器驱动（如 ChromeDriver）用于笔记下载器的登录自动化（具体要求参见 `note_downloader/README.md`）。

本项目在开发过程中已经通过了基本功能测试，但仍可能存在改进空间。欢迎贡献代码或提交 Issue。一切安装运行问题也可以在项目仓库进行讨论。希望本说明文档能帮助您顺利部署和使用 **pyqtNotepad** 多功能记事本应用！
