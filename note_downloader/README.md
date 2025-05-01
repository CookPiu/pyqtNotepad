# Moodle 笔记下载器 (Note Downloader)

本项目是一个 Python 脚本，旨在帮助用户从 Moodle 平台自动下载课程资料，并根据预设规则进行分类整理。

## 主要功能

*   **自动爬取**: 自动获取用户“我的课程”列表以及每个课程页面内的资源链接。
*   **文件下载**: 使用 `requests` 库下载识别到的课程文件。
*   **自动分类**: 根据 `config/classify_rules.yaml` 中定义的规则（基于文件名关键字、正则表达式、文件类型），将下载的文件自动归类到不同的子目录中（如 Lectures, Assignments, Exams 等）。
*   **增量下载与内容检查**:
    *   使用 `downloads/manifest.json` 文件记录已下载文件的签名。
    *   通过比较文件的文本内容签名（优先）或二进制哈希（备用）来判断文件是否有更新，避免重复下载未更改的文件。
    *   支持 PDF, PPT/PPTX, DOC/DOCX 的文本内容提取与签名，对其他文件类型使用二进制哈希。
*   **手动登录支持**: 采用 Selenium 启动浏览器，由用户手动完成登录过程（包括用户名、密码、验证码、二次验证等），脚本随后接管 Cookie 以进行后续操作，提高了对复杂登录流程的兼容性。
*   **配置灵活**: 通过 YAML 文件进行配置，方便修改目标网址、下载目录、分类规则等。
*   **日志记录**: 记录详细的运行日志，方便追踪下载过程和排查问题。
*   **断点续传 (部分支持)**: 在网络中断后，对于未完成的文件，再次运行时会尝试从中断处继续下载（基于文件大小判断）。

## 文件结构

项目采用以下结构组织文件：

```
note_downloader/
├── config/                   # 配置文件目录
│   ├── classify_rules.yaml   # 文件分类规则
│   └── config.yaml           # 主要配置文件 (Moodle URL, 下载目录等)
├── downloads/                # 默认的下载文件根目录
│   ├── manifest.json         # 已下载文件的签名清单 (自动生成/更新)
│   └── <Course Name 1>/      # 按课程名称自动创建的目录
│       ├── <Category 1>/     # 按分类规则自动创建的目录 (如 Lectures)
│       │   └── file1.pdf
│       ├── <Category 2>/
│       │   └── file2.pptx
│       └── ...
├── src/                      # Python 源代码目录
│   ├── __init__.py           # 将 src 标记为 Python 包
│   ├── checker.py            # 文件哈希/签名计算与 Manifest 处理
│   ├── classifier.py         # 文件分类逻辑
│   ├── crawler.py            # 爬取 Moodle 课程和资源链接
│   ├── downloader.py         # 文件下载与 Manifest/分类集成
│   ├── main.py               # 程序主入口脚本
│   └── utils.py              # 辅助函数 (配置加载, 日志, Selenium 会话获取等)
├── environment.yml           # Conda 环境依赖配置文件
└── README.md                 # 本说明文件
```

## 环境设置

本项目依赖于特定的 Python 库，建议使用 Conda 来管理环境。

1.  **安装 Conda**: 如果你还没有安装 Conda (Miniconda 或 Anaconda)，请先[下载并安装](https://docs.conda.io/en/latest/miniconda.html)。
2.  **创建环境**: 打开你的终端 (Terminal, PowerShell, Anaconda Prompt)，`cd` 到本项目的根目录 (`note_downloader/`)，然后运行以下命令来根据 `environment.yml` 文件创建 Conda 环境：
    ```bash
    conda env create -f environment.yml
    ```
    这将自动安装所有必需的库，包括 `requests`, `beautifulsoup4`, `pyyaml`, `selenium`, `webdriver-manager`, `lxml`, `PyPDF2`, `python-pptx`, `python-docx` 等。
3.  **激活环境**: 每次运行脚本前，都需要激活创建的环境。环境名称通常在 `environment.yml` 文件的 `name:` 字段中定义（例如，可能是 `note_downloader_env`）。使用以下命令激活：
    ```bash
    conda activate <环境名称>
    ```
    例如: `conda activate note_downloader_env`

## 配置说明

在运行脚本前，你需要配置以下两个文件：

1.  **`config/config.yaml`**:
    *   `base_url`: 你的 Moodle 网站的基础 URL (例如: `https://moodle.example.com`)。**必须填写**。
    *   `my_courses_path`: （可选）访问“我的课程”页面的相对路径，默认为 `/my/`。
    *   `login_path`: （可选）访问登录页面的相对路径，默认为 `/login/index.php`。
    *   `download_directory`: （可选）指定下载文件存放的根目录名称，默认为 `downloads`。
    *   `credentials`: **此部分在此版本中仅作占位符或配置检查用**，因为登录是手动完成的。你**不需要**在此填写用户名和密码。

2.  **`config/classify_rules.yaml`**:
    *   `type_map`: 基于文件扩展名进行分类。例如，将所有 `.pdf` 文件放入 `PDF` 目录。
    *   `keyword_map`: 基于文件名中包含的关键字进行分类（不区分大小写）。例如，文件名包含 `lecture` 或 `Lec` 的放入 `Lectures` 目录。**优先级高于 Type Match**。
    *   `regex_map`: 基于文件名匹配正则表达式进行分类（不区分大小写）。例如，文件名匹配 `Assign(ment)?\s?\d+` 的放入 `Assignments` 目录。**优先级高于 Type Match，低于 Keyword Match**。
    *   `default`: 如果文件不匹配任何上述规则，则放入此目录下，默认为 `Others`。

你可以根据自己的需求修改这些规则。

## 使用方法

1.  **确保环境已激活**: 按照“环境设置”部分的说明激活正确的 Conda 环境。
2.  **配置检查**: 确认 `config/config.yaml` 中的 `base_url` 已正确设置。确认 `config/classify_rules.yaml` 中的分类规则符合你的需求。
3.  **运行脚本**: 在终端中，确保你的当前目录是项目的根目录 (`note_downloader/`)，然后执行以下命令：
    ```bash
    python -m src.main
    ```
4.  **登录**: 脚本会启动一个 Chrome 浏览器窗口并打开 Moodle 登录页面。请在浏览器中完成所有登录步骤（输入用户名、密码，处理任何验证码或二次验证）。
5.  **自动检测与继续**: 脚本会自动检测你是否已成功登录（通过监测浏览器 URL 的变化）。一旦检测到登录成功，它将自动获取必要的 Cookie 并开始后续的爬取和下载过程，**无需你返回终端进行任何操作**。
6.  **等待下载**: 脚本开始自动爬取课程、下载文件并进行分类。你可以在终端看到详细的日志输出。下载过程中会显示进度条。
7.  **完成**: 脚本运行结束后，会输出本次运行的总结信息（总耗时、处理课程数、下载/跳过/失败文件数等）。`downloads/manifest.json` 文件也会被更新。

## 注意事项

*   **首次运行**: 首次运行时，由于没有 `manifest.json` 文件，脚本会下载所有找到的资源。
*   **网络问题**: 如果在下载过程中遇到网络错误或超时，部分文件可能会下载失败。重新运行脚本通常可以继续下载失败或未完成的文件。
*   **Moodle 页面更改**: 如果 Moodle 网站的页面结构发生较大变化，可能导致课程列表或资源链接的爬取失败。此时需要检查 `crawler.py` 中的 CSS 选择器并进行调整。如果课程列表获取失败，脚本会尝试将 `/my/` 页面的 HTML 保存到 `my_html_dump.html` 以供调试。
*   **依赖库**: 确保所有依赖库都通过 `environment.yml` 正确安装在激活的环境中。特别是 `webdriver-manager` 会自动下载和管理 ChromeDriver。
*   **文本提取库**: `PyPDF2`, `python-pptx`, `python-docx` 是可选的，用于基于文本内容的文件签名。如果未安装，脚本会回退到使用二进制哈希进行文件变更检测，这可能导致即使文件内容未变（例如仅元数据更改）也被重新下载。
