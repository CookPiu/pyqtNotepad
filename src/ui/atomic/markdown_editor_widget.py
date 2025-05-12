from PyQt6.QtWidgets import (QWidget, QToolBar, QPlainTextEdit, QStackedWidget, 
                             QVBoxLayout, QHBoxLayout, QFrame, QTextEdit) # Added QTextEdit for ExtraSelection
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRegularExpression, QSignalBlocker, QRect, QSize
from PyQt6.QtGui import (QColor, QAction, QSyntaxHighlighter, QTextCharFormat, 
                         QFont, QPainter, QTextCursor, QPalette, QPaintEvent) # Added QPaintEvent
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdownify import markdownify
import re # Added for Mermaid integration
import html # Added for HTML unescaping for Mermaid

# --- LineNumberArea for QPlainTextEdit ---
class LineNumberArea(QWidget):
    def __init__(self, editor: QPlainTextEdit):
        super().__init__(editor)
        self.editor = editor
        self._width = 40
        self.setFixedWidth(self._width)
        # Default colors, can be updated by theme
        self._background_color = QColor(Qt.GlobalColor.lightGray)
        self._text_color = QColor(Qt.GlobalColor.black)
        self._border_color = QColor(Qt.GlobalColor.darkGray)
        self.setStyleSheet(f"border-right: 1px solid {self._border_color.name()};")

    def sizeHint(self) -> QSize:
        return QSize(self._width, 0)

    def set_colors(self, background: QColor, text: QColor, border: QColor):
        self._background_color = background
        self._text_color = text
        self._border_color = border
        self.setStyleSheet(f"border-right: 1px solid {self._border_color.name()};")
        self.update()
    
    def update_width(self, width: int):
        if self._width != width:
            self._width = width
            self.setFixedWidth(width)
            self.update()

    def paintEvent(self, event: QPaintEvent): # type: ignore
        painter = QPainter(self)
        painter.fillRect(event.rect(), self._background_color)

        block = self.editor.firstVisibleBlock()
        block_number = block.blockNumber()
        # Get the top of the first visible block in viewport coordinates
        top_y_viewport = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom_y_viewport = top_y_viewport + self.editor.blockBoundingRect(block).height()
        
        font_metrics_height = self.editor.fontMetrics().height()

        while block.isValid() and top_y_viewport <= event.rect().bottom():
            if block.isVisible() and bottom_y_viewport >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(self._text_color)
                # Draw text aligned to the right, vertically centered within the line number area for that block
                paint_rect = QRect(0, int(top_y_viewport), self.width() - 6, font_metrics_height)
                painter.drawText(paint_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number)

            block = block.next()
            if not block.isValid():
                break
            
            block_geom = self.editor.blockBoundingGeometry(block)
            top_y_viewport = block_geom.translated(self.editor.contentOffset()).top()
            bottom_y_viewport = top_y_viewport + block_geom.height()
            block_number += 1

# --- Markdown-it plugin ---
def source_line_plugin(md_instance: MarkdownIt):
    def add_line_attributes_rule(state):
        for token in state.tokens:
            if token.map and token.type not in ["list_item_close", "paragraph_close", "heading_close"]:
                if token.nesting >= 0: 
                    line_start = token.map[0]
                    token.attrSet('data-source-line', str(line_start))
    md_instance.core.ruler.push('source_line_attributes', add_line_attributes_rule)

# Initialize MarkdownIt and then set options
md = MarkdownIt()
md.options['html'] = True       # Allows HTML tags in markdown to pass through.
md.options['linkify'] = True    # Autoconverts URL-like text to links.
md.options['typographer'] = False # Disables smart quotes and other typographic replacements.
# Apply plugins after setting options
md.use(source_line_plugin)

# --- Mermaid and MathJax Integration Helper Functions ---
def post_process_mermaid_blocks(html_content: str) -> str:
    """
    Converts <pre><code class="language-mermaid">...</code></pre> blocks
    to <div class="mermaid">...</div> blocks.
    """
    def unescape_match(match):
        mermaid_code = match.group(1)
        return f'<div class="mermaid">{html.unescape(mermaid_code)}</div>'

    # Regex to find <pre><code ... class="language-mermaid" ...>CONTENT</code></pre>
    # This version is robust to attribute order and other attributes.
    # It uses a positive lookahead (?=...) to ensure 'class="language-mermaid"' is present.
    mermaid_block_regex = r'<pre>\s*<code(?=[^>]*\sclass="language-mermaid")[^>]*>(.*?)</code>\s*</pre>'
    
    processed_html = re.sub(
        mermaid_block_regex,
        unescape_match,
        html_content,
        flags=re.DOTALL
    )
    return processed_html

def build_full_html_preview(html_body: str, include_mathjax: bool = True) -> str:
    """
    Wraps the given HTML body in a full HTML document structure,
    including Mermaid.js and optionally MathJax scripts and initialization.
    """
    mathjax_script_html = ""
    if include_mathjax:
        mathjax_script_html = """
      <!-- MathJax Configuration -->
      <script>
        window.MathJax = {
          tex: {
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true,
            tags: 'ams'
          },
          options: {
            skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
            ignoreHtmlClass: 'tex2jax_ignore',
            processHtmlClass: 'tex2jax_process'
          },
          svg: { fontCache: 'global' }
        };
      </script>
      <!-- MathJax Core Script -->
      <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Markdown Preview</title>
      <!-- Mermaid 核心脚本 -->
      <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
      <script>mermaid.initialize({{ startOnLoad: true }});</script>
      {mathjax_script_html}
      <style>
        body {{ margin: 0; padding: 1em; font-family: sans-serif; }}
        /* Add any other global styles for preview here */
        /* Basic MathJax styling for visibility if needed */
        .MathJax_Display {{ text-align: center; margin: 1em 0em; }}
        mjx-container[jax="SVG"] {{ direction: ltr; }} /* Ensure LTR for MathJax SVG output */
        mjx-container mjx-math {{ /* Allow horizontal scroll for single-line formulas */
            overflow-x: auto;
            overflow-y: hidden;
            display: inline-block; /* Changed from block to inline-block for better flow with text */
            max-width: 100%;
        }}
      </style>
    </head>
    <body>
      <div id="preview-content-area">
        {html_body}
      </div>
    </body>
    </html>
    """

class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self.rules = []
        h1_format = QTextCharFormat(); h1_format.setForeground(QColor("#1a1a8c")); h1_format.setFontWeight(QFont.Weight.Bold); h1_format.setFontPointSize(parent.defaultFont().pointSize()*1.5); self.rules.append((QRegularExpression(r"^#\s+.*$"),h1_format))
        h2_format = QTextCharFormat(); h2_format.setForeground(QColor("#1a5c8c")); h2_format.setFontWeight(QFont.Weight.Bold); h2_format.setFontPointSize(parent.defaultFont().pointSize()*1.3); self.rules.append((QRegularExpression(r"^##\s+.*$"),h2_format))
        h3_format = QTextCharFormat(); h3_format.setForeground(QColor("#1a8c5c")); h3_format.setFontWeight(QFont.Weight.Bold); h3_format.setFontPointSize(parent.defaultFont().pointSize()*1.15); self.rules.append((QRegularExpression(r"^###\s+.*$"),h3_format))
        bold_format = QTextCharFormat(); bold_format.setFontWeight(QFont.Weight.Bold); self.rules.append((QRegularExpression(r"\*\*(.+?)\*\*"),bold_format)); self.rules.append((QRegularExpression(r"__(.+?)__"),bold_format))
        italic_format = QTextCharFormat(); italic_format.setFontItalic(True); self.rules.append((QRegularExpression(r"\*(?!\s)(.+?)(?<!\s)\*"),italic_format)); self.rules.append((QRegularExpression(r"_(?!\s)(.+?)(?<!\s)_"),italic_format))
        inline_code_format = QTextCharFormat(); inline_code_format.setFontFamily("Consolas, Courier New, monospace"); inline_code_format.setBackground(QColor("#f0f0f0")); inline_code_format.setForeground(QColor("#c7254e")); self.rules.append((QRegularExpression(r"`([^`\n]+)`"),inline_code_format))
        
        # Generic code block format
        self.generic_code_block_format = QTextCharFormat(); self.generic_code_block_format.setFontFamily("Consolas, Courier New, monospace"); self.generic_code_block_format.setBackground(QColor("#f5f5f5"))
        
        # Mermaid block format
        self.mermaid_block_format = QTextCharFormat(); self.mermaid_block_format.setFontFamily("Consolas, Courier New, monospace"); self.mermaid_block_format.setBackground(QColor("#e0f0ff")) # Light blue background for Mermaid

        self.generic_code_block_start_expression = QRegularExpression(r"^```(?!mermaid).*$") # ``` followed by anything but mermaid
        self.mermaid_block_start_expression = QRegularExpression(r"^```mermaid\s*$")
        self.code_block_end_expression = QRegularExpression(r"^```\s*$") # Common end for all code blocks

        link_format = QTextCharFormat(); link_format.setForeground(QColor("blue")); link_format.setFontUnderline(True); self.rules.append((QRegularExpression(r"\[([^\]]+)\]\(([^\)]+)\)"),link_format))

        # Optional: Mermaid keywords for in-block highlighting (can be expanded)
        # self.mermaid_keyword_format = QTextCharFormat(); self.mermaid_keyword_format.setForeground(QColor("darkblue")); self.mermaid_keyword_format.setFontWeight(QFont.Weight.Bold)
        # self.mermaid_keywords = [r"\b(graph|sequenceDiagram|classDiagram|stateDiagram)\b", r"-->", r":"]


    def highlightBlock(self, text):
        # State definitions:
        # 0: Normal text
        # 1: Inside a generic code block (e.g., ```python)
        # 2: Inside a Mermaid code block (```mermaid)

        previous_state = self.previousBlockState()
        current_state = 0  # Default to normal text

        # Determine current block's state based on start/end expressions
        if previous_state == 1:  # Was in a generic code block
            if self.code_block_end_expression.match(text).hasMatch():
                current_state = 0  # Block ends
                self.setFormat(0, len(text), self.generic_code_block_format) # Format the closing ```
            else:
                current_state = 1  # Still in generic code block
                self.setFormat(0, len(text), self.generic_code_block_format)
        elif previous_state == 2:  # Was in a Mermaid block
            if self.code_block_end_expression.match(text).hasMatch():
                current_state = 0  # Block ends
                self.setFormat(0, len(text), self.mermaid_block_format) # Format the closing ```
            else:
                current_state = 2  # Still in Mermaid block
                self.setFormat(0, len(text), self.mermaid_block_format)
                # Optional: Apply keyword highlighting within Mermaid block
                # for keyword_pattern_str in self.mermaid_keywords:
                #     pattern = QRegularExpression(keyword_pattern_str)
                #     iterator = pattern.globalMatch(text)
                #     while iterator.hasNext():
                #         match = iterator.next()
                #         self.setFormat(match.capturedStart(), match.capturedLength(), self.mermaid_keyword_format)
        else:  # Not in any multi-line block from the previous line
            if self.mermaid_block_start_expression.match(text).hasMatch():
                self.setFormat(0, len(text), self.mermaid_block_format)
                # Check if the block also ends on this line
                if self.code_block_end_expression.match(text).hasMatch() and len(text.strip()) == len("```mermaid") + len("```") and text.strip().endswith("```"): # very simple one-liner check
                     current_state = 0 # Ends on the same line
                elif text.strip() == "```mermaid" and self.code_block_end_expression.match(text).hasMatch(): # ```mermaid```
                     current_state = 0
                elif self.code_block_end_expression.match(text).hasMatch() and text.count("```") == 2 : # e.g. ```mermaid ... ```
                    current_state = 0
                else:
                    current_state = 2 # Starts a multi-line Mermaid block
            elif self.generic_code_block_start_expression.match(text).hasMatch():
                self.setFormat(0, len(text), self.generic_code_block_format)
                # Check if the block also ends on this line
                if self.code_block_end_expression.match(text).hasMatch() and text.count("```") == 2 : # e.g. ```python ... ```
                    current_state = 0
                else:
                    current_state = 1  # Starts a multi-line generic code block
            else:
                current_state = 0 # Normal text, apply inline rules

        self.setCurrentBlockState(current_state)

        # Apply inline rules only if not in a special block or if they are designed for it
        if current_state == 0: # Only apply general inline rules to normal text
            for pattern, fmt in self.rules:
                iterator = pattern.globalMatch(text)
                while iterator.hasNext():
                    match = iterator.next()
                    self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class MarkdownEditorWidget(QWidget):
    content_changed = pyqtSignal()
    view_mode_changed = pyqtSignal(bool) 

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Editor part with line numbers
        self.editor_area_widget = QWidget(self) # Container for editor + line numbers
        editor_area_layout = QHBoxLayout(self.editor_area_widget)
        editor_area_layout.setContentsMargins(0,0,0,0)
        editor_area_layout.setSpacing(0)

        self.editor = QPlainTextEdit(self.editor_area_widget)
        self.editor.setAcceptDrops(False) # Disable drops to let MainWindow handle file drops
        self.line_numbers = LineNumberArea(self.editor) # Pass editor to LineNumberArea
        self.highlighter = MarkdownHighlighter(self.editor.document())
        
        editor_area_layout.addWidget(self.line_numbers)
        editor_area_layout.addWidget(self.editor)
        self.editor_area_widget.setLayout(editor_area_layout)

        self.preview = QWebEngineView(self)
        
        self.stacked_widget = QStackedWidget(self)
        self.editor_page_index = self.stacked_widget.addWidget(self.editor_area_widget) # Add container
        self.preview_page_index = self.stacked_widget.addWidget(self.preview)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

        self._render_timer = QTimer(self, interval=100, singleShot=True)
        self._render_timer.timeout.connect(self._render_preview_from_editor)

        # Connect signals for line number area updates
        self.editor.blockCountChanged.connect(self.update_line_number_area_width)
        self.editor.updateRequest.connect(self.update_line_number_area)
        self.editor.cursorPositionChanged.connect(self._highlight_current_line_in_editor) # Optional: current line highlight

        self.editor.textChanged.connect(self._on_editor_text_changed)
        
        # Setup custom context menu for the QPlainTextEdit
        self.editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_custom_context_menu)
        
        # Set custom context menu for the preview QWebEngineView
        self.preview.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.preview.customContextMenuRequested.connect(self.show_preview_custom_context_menu)
        
        self.is_preview_mode = False
        self._pending_preview_setup = False # Flag for JS execution after load
        self.preview.loadFinished.connect(self._on_preview_load_finished)

        self._render_preview_html("") 
        self.stacked_widget.setCurrentIndex(self.editor_page_index)
        self.update_line_number_area_width() # Initial width update

        # For current line highlight in editor (optional, similar to TextEditor)
        self._editor_current_line_selection = QTextEdit.ExtraSelection() # Use QTextEdit.ExtraSelection


    def show_custom_context_menu(self, position):
        from PyQt6.QtWidgets import QMenu, QApplication, QMainWindow # Ensure QMenu, QApplication, QMainWindow are imported
        # QAction is already imported via PyQt6.QtGui

        menu = QMenu(self.editor)
        # Try to get MainWindow instance. self.window() might be the top-level window.
        main_window = self.window() 
        if not isinstance(main_window, QMainWindow): 
            # A more robust way might be needed if self.window() isn't the MainWindow
            # For now, assume it is or try parent().
            parent_widget = self.parent()
            while parent_widget:
                if isinstance(parent_widget, QMainWindow):
                    main_window = parent_widget
                    break
                parent_widget = parent_widget.parent()

        # Standard actions
        undo_action = menu.addAction("撤销")
        undo_action.setEnabled(self.editor.document().isUndoAvailable())
        undo_action.triggered.connect(self.editor.undo)

        redo_action = menu.addAction("重做")
        redo_action.setEnabled(self.editor.document().isRedoAvailable())
        redo_action.triggered.connect(self.editor.redo)
        
        menu.addSeparator()

        cut_action = menu.addAction("剪切")
        cut_action.setEnabled(self.editor.textCursor().hasSelection())
        cut_action.triggered.connect(self.editor.cut)

        copy_action = menu.addAction("复制")
        copy_action.setEnabled(self.editor.textCursor().hasSelection())
        copy_action.triggered.connect(self.editor.copy)
        
        paste_action = menu.addAction("粘贴")
        clipboard = QApplication.clipboard()
        can_paste_text = clipboard.mimeData().hasText() and self.editor.canPaste()
        paste_action.setEnabled(can_paste_text)
        if main_window and hasattr(main_window, 'paste_action_wrapper'):
            paste_action.triggered.connect(main_window.paste_action_wrapper)
        else:
            paste_action.triggered.connect(self.editor.paste)
            print("MarkdownEditorWidget: Warning - Could not connect paste to MainWindow wrapper.")
            
        menu.addSeparator()

        select_all_action = menu.addAction("全选")
        select_all_action.triggered.connect(self.editor.selectAll)

        has_selection = self.editor.textCursor().hasSelection()
        if has_selection:
            menu.addSeparator()
            
            translate_action = menu.addAction("翻译选中内容")
            if main_window and hasattr(main_window, 'translate_selection_wrapper'):
                translate_action.triggered.connect(main_window.translate_selection_wrapper)
            else:
                translate_action.setEnabled(False)
                print("MarkdownEditorWidget: Warning - Could not connect translate to MainWindow wrapper.")

            calc_action = menu.addAction("计算选中内容")
            if main_window and hasattr(main_window, 'calculate_selection_wrapper'):
                calc_action.triggered.connect(main_window.calculate_selection_wrapper)
            else:
                calc_action.setEnabled(False)
                print("MarkdownEditorWidget: Warning - Could not connect calculate to MainWindow wrapper.")

            ai_action = menu.addAction("将选中内容复制到 AI 助手")
            if main_window and hasattr(main_window, 'copy_to_ai_wrapper'):
                ai_action.triggered.connect(main_window.copy_to_ai_wrapper)
            else:
                ai_action.setEnabled(False)
                print("MarkdownEditorWidget: Warning - Could not connect copy_to_ai to MainWindow wrapper.")

            # Add "Fetch URL Source" action for source editor
            selected_text_for_url = self.editor.textCursor().selectedText().strip()
            if selected_text_for_url:
                is_potential_url = selected_text_for_url.startswith("http://") or selected_text_for_url.startswith("https://")
                if is_potential_url:
                    menu.addSeparator()
                    fetch_action = menu.addAction("打开并抓取源码(Web视图)")
                    if main_window and hasattr(main_window, 'fetch_url_source_wrapper'):
                        fetch_action.triggered.connect(main_window.fetch_url_source_wrapper)
                    else:
                        fetch_action.setEnabled(False)
        
        menu.exec(self.editor.mapToGlobal(position))

    def show_preview_custom_context_menu(self, position):
        from PyQt6.QtWidgets import QMenu, QApplication, QMainWindow
        from PyQt6.QtWebEngineCore import QWebEnginePage
        # QAction is already imported via PyQt6.QtGui

        menu = QMenu(self.preview)
        main_window = self.window()
        if not isinstance(main_window, QMainWindow):
            parent_widget = self.parent()
            while parent_widget:
                if isinstance(parent_widget, QMainWindow):
                    main_window = parent_widget
                    break
                parent_widget = parent_widget.parent()

        # Standard Web Actions
        action_undo = self.preview.page().action(QWebEnginePage.WebAction.Undo)
        action_undo.setText("撤销")
        menu.addAction(action_undo)

        action_redo = self.preview.page().action(QWebEnginePage.WebAction.Redo)
        action_redo.setText("重做")
        menu.addAction(action_redo)
        
        menu.addSeparator()
        
        action_cut = self.preview.page().action(QWebEnginePage.WebAction.Cut)
        action_cut.setText("剪切")
        menu.addAction(action_cut)
        
        action_copy = self.preview.page().action(QWebEnginePage.WebAction.Copy)
        action_copy.setText("复制")
        menu.addAction(action_copy)
        
        action_paste = self.preview.page().action(QWebEnginePage.WebAction.Paste)
        action_paste.setText("粘贴")
        menu.addAction(action_paste)
        
        menu.addSeparator()
        
        action_select_all = self.preview.page().action(QWebEnginePage.WebAction.SelectAll)
        action_select_all.setText("全选")
        menu.addAction(action_select_all)

        has_selection = self.preview.hasSelection()
        if has_selection:
            menu.addSeparator()
            
            translate_action = menu.addAction("翻译选中内容")
            if main_window and hasattr(main_window, 'translate_selection_wrapper'):
                translate_action.triggered.connect(main_window.translate_selection_wrapper)
            else:
                translate_action.setEnabled(False)
                print("MarkdownPreview: Warning - Could not connect translate to MainWindow wrapper.")

            calc_action = menu.addAction("计算选中内容")
            if main_window and hasattr(main_window, 'calculate_selection_wrapper'):
                calc_action.triggered.connect(main_window.calculate_selection_wrapper)
            else:
                calc_action.setEnabled(False)
                print("MarkdownPreview: Warning - Could not connect calculate to MainWindow wrapper.")

            ai_action = menu.addAction("将选中内容复制到 AI 助手")
            if main_window and hasattr(main_window, 'copy_to_ai_wrapper'):
                ai_action.triggered.connect(main_window.copy_to_ai_wrapper)
            else:
                ai_action.setEnabled(False)
                print("MarkdownPreview: Warning - Could not connect copy_to_ai to MainWindow wrapper.")

            # Add "Fetch URL Source" action for preview
            selected_text_for_url_preview = self.preview.selectedText().strip()
            if selected_text_for_url_preview:
                is_potential_url_preview = selected_text_for_url_preview.startswith("http://") or selected_text_for_url_preview.startswith("https://")
                if is_potential_url_preview:
                    menu.addSeparator()
                    fetch_action_preview = menu.addAction("打开并抓取源码(Web视图)")
                    if main_window and hasattr(main_window, 'fetch_url_source_wrapper'):
                        fetch_action_preview.triggered.connect(main_window.fetch_url_source_wrapper)
                    else:
                        fetch_action_preview.setEnabled(False)
        
        menu.exec(self.preview.mapToGlobal(position))

    def _on_preview_load_finished(self, success: bool):
        if success and self._pending_preview_setup and self.is_preview_mode:
            print("[MarkdownEditorWidget] Preview load finished, applying settings.")
            if self.preview.page():
                # Check if document.body exists before trying to set contentEditable
                self.preview.page().runJavaScript(
                    "if(document.body) { document.body.contentEditable = 'true'; } else { console.error('JS Error: document.body is null when trying to set contentEditable.'); }"
                )
                
                block_to_scroll = getattr(self, '_scroll_to_block_on_preview_load', 0)
                
                scroll_js = (f"const targetElement = document.querySelector('[data-source-line=\"{block_to_scroll}\"]');"
                             "if (targetElement) { targetElement.scrollIntoView({ behavior: 'auto', block: 'start' }); }"
                             "else { console.log('Scroll target not found for block " + str(block_to_scroll) + ", scrolling to top.'); window.scrollTo(0, 0); }")
                self.preview.page().runJavaScript(scroll_js)
                self.preview.setFocus()
            self._pending_preview_setup = False
        elif not success:
            print("[MarkdownEditorWidget] Preview load failed.")
        
        # Try to force MathJax to re-typeset if it missed the initial load.
        # This is a bit of a hack, ideally MathJax handles dynamic content.
        if success and self.is_preview_mode:
            if self.preview.page():
                QTimer.singleShot(350, lambda: self.preview.page().runJavaScript( # Increased delay slightly
                    """
                    if (typeof MathJax !== 'undefined' && MathJax.typesetPromise) {
                        console.log('Forcing MathJax typesetPromise on #preview-content-area');
                        const container = document.getElementById('preview-content-area');
                        if (container) {
                            MathJax.typesetPromise([container]).then(() => {
                                console.log('MathJax typesetPromise on container completed.');
                            }).catch((err) => {
                                console.error('MathJax typesetPromise on container failed:', err);
                            });
                        } else {
                            console.error('#preview-content-area not found for MathJax. Falling back to global typeset.');
                            MathJax.typesetPromise().then(() => {
                                console.log('MathJax global typesetPromise completed (fallback).');
                            }).catch((err) => {
                                console.error('MathJax global typesetPromise failed (fallback):', err);
                            });
                        }
                    } else {
                        console.log('MathJax or typesetPromise not ready for force re-render on #preview-content-area');
                    }
                    """
                ))


    def update_line_number_area_width(self):
        width = self.line_number_area_width_calculator()
        self.line_numbers.update_width(width)

    def line_number_area_width_calculator(self) -> int:
        digits = len(str(max(1, self.editor.document().blockCount())))
        space = self.editor.fontMetrics().horizontalAdvance('9') * digits + 12 # Adjust padding
        return max(40, space)

    def update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self.line_numbers.scroll(0, dy)
        else:
            self.line_numbers.update(0, rect.y(), self.line_numbers.width(), rect.height())
        if rect.contains(self.editor.viewport().rect()):
            self.update_line_number_area_width()
            
    def _highlight_current_line_in_editor(self): # Optional
        # This is a simplified version. TextEditor has more robust theming for this.
        selections = []
        if not self.editor.isReadOnly(): # Check read-only status on the editor instance
            selection = QTextEdit.ExtraSelection() # Use QTextEdit.ExtraSelection
            line_color = QColor(Qt.GlobalColor.yellow).lighter(160) # Example color
            # Theme manager should provide this color
            # For now, using a default. It can be updated by update_editor_theme_colors
            if hasattr(self, '_current_line_highlight_color_editor'):
                line_color = self._current_line_highlight_color_editor

            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.cursor = self.editor.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)
        self.editor.setExtraSelections(selections)


    def _on_editor_text_changed(self):
        if not self.is_preview_mode:
            self._render_timer.start()

    def _render_preview_from_editor(self):
        current_text = self.editor.toPlainText()
        self._render_preview_html(current_text)
        self.content_changed.emit()

    def _render_preview_html(self, markdown_text: str):
        try:
            print("\n--- [MarkdownEditorWidget] Rendering Preview ---")
            print(f"[MarkdownEditorWidget] Input Markdown Text (first 100 chars): {markdown_text[:100].encode('utf-8', 'replace').decode('utf-8')}")
            
            # Step 1: Render base HTML from Markdown
            # LaTeX formulas like \(...\) and \[...\] should be passed through by markdown-it
            # if it doesn't have a specific (conflicting) math plugin.
            # MathJax will then pick them up in the browser.
            html_body = md.render(markdown_text)
            
            # --- DEBUGGING PRINT ---
            if R"(\()" in markdown_text or R"(\[)" in markdown_text or "$" in markdown_text:
                print(f"DEBUG [MarkdownEditorWidget] md.render() output for text containing LaTeX-like sequences (first 500 chars of html_body):\n{html_body[:500].encode('utf-8', 'replace').decode('utf-8')}")
            # --- END DEBUGGING PRINT ---
            
            # print(f"[MarkdownEditorWidget] Full md.render() output for debugging: {html_body.encode('utf-8', 'replace').decode('utf-8')}") # DEBUG: Full output

            if "language-mermaid" in html_body:
                print("[MarkdownEditorWidget] 'language-mermaid' DETECTED in md.render() output.")
                try:
                    start_index = html_body.find("language-mermaid")
                    # Print some context around it
                    context_start = max(0, start_index - 150) # 150 chars before
                    context_end = min(len(html_body), start_index + 250) # 250 chars after "language-mermaid"
                    print(f"[MarkdownEditorWidget] HTML snippet around 'language-mermaid':\n---\n{html_body[context_start:context_end].encode('utf-8', 'replace').decode('utf-8')}\n---")
                except Exception as e_find:
                    print(f"[MarkdownEditorWidget] Error trying to find/print snippet: {e_find}")
            else:
                print("[MarkdownEditorWidget] 'language-mermaid' NOT detected in md.render() output.")

            # Step 3: Process for Mermaid diagrams
            html_body_with_mermaid_divs = post_process_mermaid_blocks(html_body) # html_body here is after math preprocessing
            
            # Check transformation result based on the presence of language-mermaid in original and div.mermaid in processed
            original_had_mermaid_lang = "language-mermaid" in html_body # Check in the HTML *before* mermaid div transform
            transformed_has_div_mermaid = "class=\"mermaid\"" in html_body_with_mermaid_divs
            
            if original_had_mermaid_lang:
                if transformed_has_div_mermaid and "language-mermaid" not in html_body_with_mermaid_divs: # Check if original class is removed
                    print("[MarkdownEditorWidget] Mermaid block successfully transformed to <div class='mermaid'>.")
                else: # language-mermaid was present, but transformation didn't result in ONLY div.mermaid
                    print("[MarkdownEditorWidget] WARNING: 'language-mermaid' block found but transformation to <div class='mermaid'> FAILED or was incomplete.")
                    print(f"[MarkdownEditorWidget] For post_process_mermaid_blocks() (first 300 chars of result): {html_body_with_mermaid_divs[:300].encode('utf-8', 'replace').decode('utf-8')}")
            elif transformed_has_div_mermaid: # No language-mermaid initially, but div.mermaid appeared
                 print("[MarkdownEditorWidget] Found <div class='mermaid'> after post-processing (original did not have 'language-mermaid').")
            # else: # No language-mermaid and no div.mermaid (This is normal if no mermaid code was present)
                # print("[MarkdownEditorWidget] NOTE: No 'language-mermaid' block found and no <div class='mermaid'> created.")

            # Step 4: Wrap in full HTML with necessary scripts (Mermaid + MathJax)
            full_html = build_full_html_preview(html_body_with_mermaid_divs, include_mathjax=True)
            # print(f"[MarkdownEditorWidget] Full HTML for preview (first 500 chars): {full_html[:500].encode('utf-8', 'replace').decode('utf-8')}")
            
            if self.preview.page(): self.preview.page().setHtml(full_html)
            else: self.preview.setHtml(full_html)
            print("--- [MarkdownEditorWidget] Preview Rendering Attempted ---")
        except Exception as e:
            print(f"[MarkdownEditorWidget] Error rendering Markdown for preview: {e}")
            # Ensure error message also gets the full HTML structure
            error_message_html = build_full_html_preview(f"<pre>Error rendering Markdown:\n{e}</pre>", include_mathjax=True)
            if self.preview.page(): self.preview.page().setHtml(error_message_html)
            else: self.preview.setHtml(error_message_html)

    def _sync_preview_to_editor(self, html_content: str, scroll_percentage: float | None = 0.0):
        try:
            converted_markdown = markdownify(html_content, heading_style='atx', bullets='*')
            with QSignalBlocker(self.editor): self.editor.setPlainText(converted_markdown)
            self._render_preview_html(converted_markdown) 
            self.editor.document().setModified(True); self.content_changed.emit()
            if scroll_percentage is not None:
                scrollbar = self.editor.verticalScrollBar()
                QTimer.singleShot(0, lambda: scrollbar.setValue(int(scroll_percentage * scrollbar.maximum())) if scrollbar.maximum() > 0 else scrollbar.setValue(0))
        except Exception as e: print(f"Error converting HTML to Markdown or scrolling: {e}")

    def _handle_preview_scroll_and_initiate_sync(self, scroll_data):
        scroll_percentage = 0.0
        if isinstance(scroll_data, list) and len(scroll_data) == 2 and all(isinstance(item, (int, float)) for item in scroll_data):
            scroll_y, scroll_height = scroll_data
            if scroll_height > 0: scroll_percentage = scroll_y / scroll_height
        if self.preview.page(): self.preview.page().toHtml(lambda html_content: self._sync_preview_to_editor(html_content, scroll_percentage)) # This syncs content
        else: self._sync_preview_to_editor("", 0.0) # Fallback if page doesn't exist

    def _apply_preview_scroll_to_editor(self, scroll_data):
        """
        Applies the scroll percentage from the preview to the editor.
        Called when switching from Preview to Editor mode.
        Does NOT sync content from preview to editor to avoid data loss with JS-rendered elements.
        """
        scroll_percentage = 0.0
        if isinstance(scroll_data, list) and len(scroll_data) == 2 and all(isinstance(item, (int, float)) for item in scroll_data):
            scroll_y, scroll_height = scroll_data
            if scroll_height > 0: scroll_percentage = scroll_y / scroll_height
        
        scrollbar = self.editor.verticalScrollBar()
        QTimer.singleShot(0, lambda: scrollbar.setValue(int(scroll_percentage * scrollbar.maximum())) if scrollbar.maximum() > 0 else scrollbar.setValue(0))
        # Editor content remains the source of truth.

    def set_preview_visible(self, show_preview: bool):
        mode_actually_changed = False
        if show_preview:
            if not self.is_preview_mode or self.stacked_widget.currentWidget() != self.preview:
                current_editor_text = self.editor.toPlainText()
                # Store current block number for scrolling after load
                self._scroll_to_block_on_preview_load = self.editor.textCursor().blockNumber() 
                self._render_preview_html(current_editor_text) # This will trigger loadFinished
                
                self.stacked_widget.setCurrentIndex(self.preview_page_index)
                self._pending_preview_setup = True # Set flag for _on_preview_load_finished
                self.is_preview_mode = True; mode_actually_changed = True
        else: 
            if self.is_preview_mode or self.stacked_widget.currentWidget() != self.editor_area_widget: # Check against editor_area_widget
                if self.preview.page():
                    # Disable editing when switching away from preview
                    self.preview.page().runJavaScript("if(document.body) document.body.contentEditable = 'false';")
                    # Get scroll position from preview and apply to editor
                    self.preview.page().runJavaScript("[window.scrollY, document.documentElement.scrollHeight];", self._apply_preview_scroll_to_editor)
                
                self._pending_preview_setup = False # Ensure flag is reset
                self.stacked_widget.setCurrentIndex(self.editor_page_index) # Switch to editor_area_widget
                self.editor.setFocus()
                self.is_preview_mode = False
                mode_actually_changed = True
        
        # 无论模式是否实际改变，都发出信号，确保UI状态与实际状态同步
        # 这修复了在某些情况下UI状态与实际预览状态不同步的bug
        self.view_mode_changed.emit(self.is_preview_mode)

    def load_markdown(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
            with QSignalBlocker(self.editor): self.editor.setPlainText(content)
            self._render_preview_html(content); self.editor.document().setModified(False)
            self.editor.verticalScrollBar().setValue(0)
            if self.preview.page(): QTimer.singleShot(100, lambda: self.preview.page().runJavaScript("window.scrollTo(0, 0);"))
            if self.is_preview_mode:
                 QTimer.singleShot(150, lambda: self.preview.page().runJavaScript("document.body.contentEditable = 'true';") if self.preview.page() else None)
                 self.preview.setFocus()
            else: self.editor.setFocus()
            return True
        except Exception as e: print(f"Error loading Markdown file {file_path}: {e}"); return False

    def save_markdown(self, file_path: str) -> bool:
        try:
            if self.is_preview_mode: print("Warning: Saving while in preview mode. Content from source editor will be saved.")
            content = self.editor.toPlainText()
            with open(file_path, 'w', encoding='utf-8') as f: f.write(content)
            self.editor.document().setModified(False); return True
        except Exception as e: print(f"Error saving Markdown file {file_path}: {e}"); return False

    def get_content(self) -> str: return self.editor.toPlainText()
    def set_content(self, text: str):
        with QSignalBlocker(self.editor): self.editor.setPlainText(text)
        self._render_preview_html(text)
    def clear_content(self):
        with QSignalBlocker(self.editor): self.editor.clear()
        self._render_preview_html("")

    def set_preview_background_color(self, color: QColor):
        js_script = (f"if(document.body) {{ document.body.style.backgroundColor = '{color.name()}'; }} "
                     f"else if(document.documentElement) {{ document.documentElement.style.backgroundColor = '{color.name()}'; }}")
        if self.preview.page(): self.preview.page().runJavaScript(js_script)

    def get_text_edit_widget(self) -> QPlainTextEdit: return self.editor

    # Method to update line number colors from theme manager
    def update_editor_theme_colors(self, text_color: QColor, background_color: QColor, border_color: QColor, current_line_bg_color: QColor):
        self.line_numbers.set_colors(background_color, text_color, border_color)
        
        palette = self.editor.palette()
        palette.setColor(QPalette.ColorRole.Base, background_color)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        # TODO: Set selection colors from theme if needed
        # palette.setColor(QPalette.ColorRole.Highlight, QColor("#ADD6FF")) 
        # palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
        self.editor.setPalette(palette)
        
        # Store and apply current line highlight color
        self._current_line_highlight_color_editor = current_line_bg_color
        self._highlight_current_line_in_editor() # Re-apply to make it visible


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__(); self.setWindowTitle("Markdown Editor Widget Test")
            self.markdown_widget = MarkdownEditorWidget(self)
            self.setCentralWidget(self.markdown_widget)
            self.setGeometry(100,100,800,600); toolbar = QToolBar("Test"); self.addToolBar(toolbar)
            self.preview_action = QAction("Toggle Preview",self,checkable=True); self.preview_action.setChecked(False) 
            self.preview_action.triggered.connect(self.toggle_view); toolbar.addAction(self.preview_action)
            self.markdown_widget.view_mode_changed.connect(self.preview_action.setChecked)
            self.markdown_widget.set_content("# Hello Markdown!\n\nThis is a **test**.\n\n* Item 1\n* Item 2\n\n```python\nprint('Hello')\n```\n\nVisit [Google](https://www.google.com)\n\n" + "\n".join([f"Line {i}" for i in range(50)]))
        def toggle_view(self,checked): self.markdown_widget.set_preview_visible(checked)
    app = QApplication(sys.argv); window = TestWindow(); window.show(); sys.exit(app.exec())
