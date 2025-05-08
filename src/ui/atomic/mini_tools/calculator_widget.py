# src/ui/atomic/mini_tools/calculator_widget.py
import sys
import math
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGridLayout, QLineEdit, QApplication,
                              QStackedWidget, QCheckBox, QButtonGroup, QMessageBox, QSizePolicy) # Added QSizePolicy
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QColor

# Correct relative import from atomic/mini_tools to core
from ...core.base_widget import BaseWidget
# from ...core.theme_manager import ThemeManager # Optional: if needed directly

# --- Expression Evaluator Helper Class ---
class ExpressionEvaluator:
    """表达式计算器类，实现简单的表达式解析和计算"""
    def __init__(self):
        self.constants = {
            'pi': math.pi, 'e': math.e, 'phi': (1 + math.sqrt(5)) / 2,
            'c': 299792458, 'g': 9.80665,
        }
        self.functions = {
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'asin': math.asin, 'acos': math.acos, 'atan': math.atan,
            'sqrt': math.sqrt, 'log': math.log10, 'ln': math.log,
            'abs': abs, 'exp': math.exp, 'rad': math.radians, 'deg': math.degrees,
            'round': round, 'floor': math.floor, 'ceil': math.ceil,
        }
        self.units = {
            'm_to_cm': lambda x: x * 100, 'cm_to_m': lambda x: x / 100,
            'm_to_km': lambda x: x / 1000, 'km_to_m': lambda x: x * 1000,
            'm_to_in': lambda x: x * 39.3701, 'in_to_m': lambda x: x / 39.3701,
            'm_to_ft': lambda x: x * 3.28084, 'ft_to_m': lambda x: x / 3.28084,
            'kg_to_g': lambda x: x * 1000, 'g_to_kg': lambda x: x / 1000,
            'kg_to_lb': lambda x: x * 2.20462, 'lb_to_kg': lambda x: x / 2.20462,
            'c_to_f': lambda x: x * 9/5 + 32, 'f_to_c': lambda x: (x - 32) * 5/9,
            'c_to_k': lambda x: x + 273.15, 'k_to_c': lambda x: x - 273.15,
        }

    def evaluate(self, expression):
        """计算数学表达式的值"""
        try:
            # Basic safety: remove potential harmful builtins
            safe_globals = {"__builtins__": {}}
            safe_locals = {**self.constants, **self.functions, **self.units, 'convert': self._convert_unit_wrapper}

            # Replace user-friendly symbols
            expression = expression.replace('×', '*').replace('÷', '/').replace('^', '**')
            expression = expression.replace('π', 'pi') # Allow direct pi symbol

            # Evaluate
            result = eval(expression, safe_globals, safe_locals)
            return result
        except Exception as e:
            # Provide more specific error messages
            if isinstance(e, SyntaxError):
                raise ValueError(f"语法错误: {e}")
            elif isinstance(e, NameError):
                raise ValueError(f"未知名称: {e}")
            elif isinstance(e, TypeError):
                 raise ValueError(f"类型错误: {e}")
            else:
                 raise ValueError(f"计算错误: {e}")

    def _convert_unit_wrapper(self, value, unit_converter_name):
        """Wrapper for unit conversion to be used in eval"""
        if unit_converter_name in self.units:
            try:
                return self.units[unit_converter_name](value)
            except Exception as e:
                raise ValueError(f"单位转换 '{unit_converter_name}' 错误: {e}")
        else:
            raise NameError(f"未知单位转换: {unit_converter_name}")


# --- Calculator Widget ---
class CalculatorWidget(BaseWidget):
    """
    计算器原子组件，提供标准、科学和表达式计算模式。
    继承自 BaseWidget。
    """
    def __init__(self, parent=None):
        self.evaluator = ExpressionEvaluator()
        super().__init__(parent) # Calls _init_ui, _connect_signals, _apply_theme
        self.reset_calculator() # Initialize state after UI setup

    def _init_ui(self):
        """初始化计算器 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8) # Reduced spacing
        main_layout.setContentsMargins(10, 10, 10, 10) # Reduced margins

        # --- Display Frame (Wrapped in a QFrame for card-like appearance) ---
        outer_display_frame = QWidget() # Using QWidget as a simple container, can be QFrame if specific QFrame features needed for QSS
        outer_display_frame.setObjectName("calcOuterDisplayFrame") # For QSS styling (shadow etc.)
        outer_display_layout = QVBoxLayout(outer_display_frame)
        outer_display_layout.setContentsMargins(0,0,0,0) # Outer frame controls padding via QSS

        display_frame_content = QWidget() # Original display_frame becomes content
        display_frame_content.setObjectName("calcDisplayFrameContent") # Keep separate object name if needed
        display_layout = QVBoxLayout(display_frame_content)
        display_layout.setContentsMargins(5, 5, 5, 5) # Inner padding for content

        self.history_display = QLabel("")
        self.history_display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.history_display.setFont(QFont("Arial", 10)) # Smaller font
        self.history_display.setStyleSheet("color: #7f8c8d; margin-bottom: 2px;")
        display_layout.addWidget(self.history_display)
        self.display = QLineEdit("0")
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        # Font will be set in update_styles as per feedback's QSS part for display
        # self.display.setFont(QFont("Arial", 20, QFont.Weight.Bold)) 
        self.display.setFixedHeight(52) # As per feedback
        # Stylesheet will be set in update_styles
        # self.display.setStyleSheet("border: none; background-color: transparent; color: #2c3e50; padding: 3px;")
        self.display.textChanged.connect(self.on_display_changed)
        display_layout.addWidget(self.display)
        
        outer_display_layout.addWidget(display_frame_content) # Add content widget to outer frame
        main_layout.addWidget(outer_display_frame) # Add outer frame to main layout

        # --- Mode Selection Frame (Using QPushButtons as Segmented Buttons) ---
        mode_frame = QWidget()
        mode_frame.setObjectName("calcModeFrame")
        mode_button_layout = QHBoxLayout(mode_frame) # Renamed layout
        mode_button_layout.setContentsMargins(0, 0, 0, 0) # No external margins for the layout itself
        mode_button_layout.setSpacing(0) # Buttons will touch if QSS doesn't separate

        self.mode_button_group = QButtonGroup(self) # Renamed group
        self.mode_button_group.setExclusive(True)

        modes = ["标准", "科学", "表达式"]
        self.mode_buttons = {} # To store QPushButtons

        for i, mode_text in enumerate(modes):
            btn = QPushButton(mode_text)
            btn.setCheckable(True)
            btn.setObjectName(f"modeButton{mode_text.replace(' ', '')}") # Object name for QSS
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            mode_button_layout.addWidget(btn)
            self.mode_button_group.addButton(btn, i) # Add with ID for easy switching
            self.mode_buttons[mode_text] = btn
        
        main_layout.addWidget(mode_frame)

        # --- Stacked Widget for Modes ---
        self.stacked_widget = QStackedWidget()
        self.standard_calculator = QWidget()
        self._setup_standard_calculator_content(self.standard_calculator)
        self.stacked_widget.addWidget(self.standard_calculator)
        self.scientific_calculator = QWidget()
        self._setup_scientific_calculator_content(self.scientific_calculator)
        self.stacked_widget.addWidget(self.scientific_calculator)
        self.expression_calculator = QWidget()
        self._setup_expression_calculator_content(self.expression_calculator)
        self.stacked_widget.addWidget(self.expression_calculator)
        main_layout.addWidget(self.stacked_widget)

        # Default mode
        # self.standard_mode.setChecked(True) # Old checkbox
        if "标准" in self.mode_buttons:
            self.mode_buttons["标准"].setChecked(True) # Set new button as default
        self.display.setReadOnly(True) # Standard/Scientific are read-only

        # Apply initial styles
        self._apply_common_frame_style([display_frame, mode_frame])
        # self._apply_common_checkbox_style is now obsolete for mode switchers
        # self._apply_common_checkbox_style([self.standard_mode, self.scientific_mode, self.expression_mode])

    def _setup_standard_calculator_content(self, parent_widget):
        """创建标准计算器按钮布局"""
        outer_layout = QVBoxLayout(parent_widget) # This layout is for the parent_widget of the stacked_widget
        outer_layout.setContentsMargins(0, 0, 0, 0)

        outer_buttons_frame = QWidget() # New outer frame for card style
        outer_buttons_frame.setObjectName("calcOuterStdButtonsFrame")
        layout = QVBoxLayout(outer_buttons_frame) # Layout for the new outer frame
        layout.setContentsMargins(0,0,0,0) # Outer frame will control padding via QSS

        buttons_frame_content = QWidget() # Original buttons_frame becomes content
        buttons_frame_content.setObjectName("calcStdButtonsFrameContent")
        buttons_layout = QGridLayout(buttons_frame_content)
        buttons_layout.setHorizontalSpacing(8) # As per feedback
        buttons_layout.setVerticalSpacing(8)   # As per feedback

        # Add row/column stretch for standard calculator
        for r in range(5): # 5 rows of buttons: C/⌫/±/÷, 7/8/9/×, ..., 0/./=
            buttons_layout.setRowStretch(r, 1)
        for c in range(4): # 4 columns
            buttons_layout.setColumnStretch(c, 1)

        buttons = [
            ('C', 0, 0, 1, 1, '#e74c3c'), ('⌫', 0, 1, 1, 1, '#e67e22'),
            ('±', 0, 2, 1, 1, '#3498db'), ('÷', 0, 3, 1, 1, '#3498db'),
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('×', 1, 3, 1, 1, '#3498db'),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('-', 2, 3, 1, 1, '#3498db'),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('+', 3, 3, 1, 1, '#3498db'),
            ('0', 4, 0, 1, 2), ('.', 4, 2), ('=', 4, 3, 1, 1, '#2ecc71'),
        ]
        self._create_buttons(buttons, buttons_layout)
        layout.addWidget(buttons_frame_content) # Add content to new outer frame's layout
        outer_layout.addWidget(outer_buttons_frame) # Add outer frame to parent_widget's layout
        # self._apply_common_frame_style([buttons_frame]) # Style will be applied to outer_buttons_frame

    def _setup_scientific_calculator_content(self, parent_widget):
        """创建科学计算器按钮布局"""
        outer_layout = QVBoxLayout(parent_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        outer_buttons_frame = QWidget()
        outer_buttons_frame.setObjectName("calcOuterSciButtonsFrame")
        layout = QVBoxLayout(outer_buttons_frame)
        layout.setContentsMargins(0,0,0,0)

        buttons_frame_content = QWidget()
        buttons_frame_content.setObjectName("calcSciButtonsFrameContent")
        buttons_layout = QGridLayout(buttons_frame_content)
        buttons_layout.setHorizontalSpacing(8) # As per feedback
        buttons_layout.setVerticalSpacing(8)   # As per feedback

        # Add row/column stretch for scientific calculator (7 rows, 5 columns)
        for r in range(7): 
            buttons_layout.setRowStretch(r, 1)
        for c in range(5):
            buttons_layout.setColumnStretch(c, 1)
            
        buttons = [
            ('sin', 0, 0, 1, 1, '#9b59b6'), ('cos', 0, 1, 1, 1, '#9b59b6'),
            ('tan', 0, 2, 1, 1, '#9b59b6'), ('π', 0, 3, 1, 1, '#9b59b6'),
            ('e', 0, 4, 1, 1, '#9b59b6'),
            ('x²', 1, 0, 1, 1, '#9b59b6'), ('x³', 1, 1, 1, 1, '#9b59b6'),
            ('xʸ', 1, 2, 1, 1, '#9b59b6'), ('√', 1, 3, 1, 1, '#9b59b6'),
            ('ln', 1, 4, 1, 1, '#9b59b6'),
            ('(', 2, 0, 1, 1, '#3498db'), (')', 2, 1, 1, 1, '#3498db'),
            ('C', 2, 2, 1, 1, '#e74c3c'), ('⌫', 2, 3, 1, 1, '#e67e22'),
            ('÷', 2, 4, 1, 1, '#3498db'),
            ('7', 3, 0), ('8', 3, 1), ('9', 3, 2), ('×', 3, 3, 1, 1, '#3498db'),
            ('1/x', 3, 4, 1, 1, '#9b59b6'),
            ('4', 4, 0), ('5', 4, 1), ('6', 4, 2), ('-', 4, 3, 1, 1, '#3498db'),
            ('±', 4, 4, 1, 1, '#3498db'),
            ('1', 5, 0), ('2', 5, 1), ('3', 5, 2), ('+', 5, 3, 1, 1, '#3498db'),
            ('log', 5, 4, 1, 1, '#9b59b6'),
            ('0', 6, 0, 1, 2), ('.', 6, 2), ('=', 6, 3, 1, 2, '#2ecc71'),
        ]
        self._create_buttons(buttons, buttons_layout, scientific=True)
        layout.addWidget(buttons_frame_content)
        outer_layout.addWidget(outer_buttons_frame)
        # self._apply_common_frame_style([buttons_frame])

    def _setup_expression_calculator_content(self, parent_widget):
        """创建表达式计算器按钮布局"""
        outer_layout = QVBoxLayout(parent_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0) # Outer frame will handle top margin if needed via QSS

        outer_buttons_frame = QWidget()
        outer_buttons_frame.setObjectName("calcOuterExprButtonsFrame")
        layout = QVBoxLayout(outer_buttons_frame) # Layout for outer frame
        layout.setContentsMargins(0, 5, 0, 0) # Original top margin now inside the card

        info_label = QLabel("输入表达式，支持函数(sin,cos,ln,sqrt...),常量(pi,e),单位转换(convert(val, m_to_cm))")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10px; color: #7f8c8d; padding: 3px; background-color: transparent;")
        layout.addWidget(info_label) # Info label inside the card

        buttons_frame_content = QWidget()
        buttons_frame_content.setObjectName("calcExprButtonsFrameContent")
        buttons_layout = QGridLayout(buttons_frame_content)
        buttons_layout.setSpacing(5)

        function_buttons = [
            ('sin', 0, 0), ('cos', 0, 1), ('tan', 0, 2), ('ln', 0, 3), ('log', 0, 4),
            ('asin', 1, 0), ('acos', 1, 1), ('atan', 1, 2), ('exp', 1, 3), ('sqrt', 1, 4)
        ]
        for func_name, row, col in function_buttons:
            button = QPushButton(func_name)
            button.setStyleSheet("background-color: #9b59b6; color: white;")
            button.clicked.connect(lambda checked, f=func_name: self.insert_function(f))
            buttons_layout.addWidget(button, row, col)

        constants = [('pi', 2, 0), ('e', 2, 1), ('phi', 2, 2), ('c', 2, 3), ('g', 2, 4)]
        for const_name, row, col in constants:
            button = QPushButton(const_name)
            button.setStyleSheet("background-color: #9b59b6; color: white;")
            button.clicked.connect(lambda checked, c=const_name: self.insert_text(c))
            buttons_layout.addWidget(button, row, col)

        operators = [
            ('(', 3, 0), (')', 3, 1), ('+', 3, 2), ('-', 3, 3), ('*', 3, 4),
            ('/', 4, 0), ('^', 4, 1), ('%', 4, 2), (',', 4, 3), ('=', 4, 4)
        ]
        for op_text, row, col in operators:
            button = QPushButton(op_text)
            color = "#2ecc71" if op_text == "=" else "#3498db"
            button.setStyleSheet(f"background-color: {color}; color: white;")
            if op_text == "=": button.clicked.connect(self.calculate_expression)
            else: button.clicked.connect(lambda checked, o=op_text: self.insert_text(o))
            buttons_layout.addWidget(button, row, col)

        unit_conversions = [
            ('m→cm', 5, 0, 'm_to_cm'), ('cm→m', 5, 1, 'cm_to_m'),
            ('kg→lb', 5, 2, 'kg_to_lb'), ('C→F', 5, 3, 'c_to_f'),
            ('Help', 5, 4, None) # Help button
        ]
        for btn_text, row, col, unit_code in unit_conversions:
            button = QPushButton(btn_text)
            if unit_code:
                button.setStyleSheet("background-color: #e67e22; color: white;")
                button.clicked.connect(lambda checked, u=unit_code: self.insert_unit_conversion(u))
            else: # Help button
                button.setStyleSheet("background-color: #7f8c8d; color: white;")
                button.clicked.connect(self.show_expression_help)
            buttons_layout.addWidget(button, row, col)

        clear_button = QPushButton("清除")
        clear_button.setStyleSheet("background-color: #e74c3c; color: white;")
        clear_button.clicked.connect(self.reset_calculator)
        buttons_layout.addWidget(clear_button, 6, 0, 1, 5) # Span full width
        
        layout.addWidget(buttons_frame_content) # Add button content to outer frame's layout
        outer_layout.addWidget(outer_buttons_frame) # Add outer frame to parent_widget's layout
        # self._apply_common_frame_style([buttons_frame])
        # self._apply_common_button_style will be handled by update_styles


    def _create_buttons(self, button_definitions, layout, scientific=False):
        """Helper to create calculator buttons"""
        button_style_map = {}
        for data in button_definitions:
            text = data[0]
            row, col = data[1], data[2]
            row_span = data[3] if len(data) > 3 else 1
            col_span = data[4] if len(data) > 4 else 1
            color = data[5] if len(data) > 5 else '#ecf0f1' # Default color

            button = QPushButton(text)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            # Set min-width: 0 for digit buttons, as per feedback
            if text.isdigit() or text == '.':
                button.setMinimumWidth(0)

            # Store style info, apply later in update_styles
            button_style_map[button] = {'color': color, 'text': text, 'scientific': scientific} # Pass scientific flag
            button.clicked.connect(self.button_clicked)
            layout.addWidget(button, row, col, row_span, col_span)
        # Store map for theme updates
        if scientific:
            self._sci_button_style_map = button_style_map
        else:
            self._std_button_style_map = button_style_map
        
        # Store all buttons created by this method for easier access in update_styles
        if not hasattr(self, '_all_calculator_buttons'):
            self._all_calculator_buttons = []
        for btn in button_style_map.keys():
            if btn not in self._all_calculator_buttons:
                 self._all_calculator_buttons.append(btn)


    def _connect_signals(self):
        """连接信号与槽"""
        # self.standard_mode.toggled.connect(self.switch_calculator_mode) # Old
        # self.scientific_mode.toggled.connect(self.switch_calculator_mode) # Old
        # self.expression_mode.toggled.connect(self.switch_calculator_mode) # Old
        self.mode_button_group.idClicked.connect(self.switch_calculator_mode_by_id)

    def _apply_theme(self):
        """应用主题样式 (由 BaseWidget 调用)"""
        self.update_styles(is_dark=False) # Default to light

    def update_styles(self, is_dark: bool):
        """根据主题更新控件样式"""
        # General theme colors
        bg_color = "rgba(45, 45, 45, 0.9)" if is_dark else "rgba(240, 240, 240, 0.9)" # Slightly less transparent
        text_color = "#F0F0F0" if is_dark else "#1A1A1A" # Higher contrast text
        history_text_color = "#A0A0A0" if is_dark else "#666666"
        border_color = "#505050" if is_dark else "#D0D0D0"
        display_bg = "rgba(0,0,0,0.05)" if is_dark else "rgba(255,255,255,0.1)" # Subtle display bg

        # Button color scheme from user feedback
        COLOR_MAP_LIGHT = {
            "digit": ("#F5F6FA", "#333333"), # background, text
            "op_primary": ("#2962FF", "white"),
            "op_secondary": ("#9C27B0", "white"),
            "danger": ("#E53935", "white"),
            "warning": ("#FB8C00", "white"),
            "default": ("#E0E0E0", "#333333") # For buttons like ( ) etc.
        }
        COLOR_MAP_DARK = { # Adjust dark theme colors for similar visual hierarchy
            "digit": ("#4A4A4A", "#F0F0F0"),
            "op_primary": ("#448AFF", "white"), # Slightly lighter blue for dark bg
            "op_secondary": ("#BA68C8", "white"), # Slightly lighter purple
            "danger": ("#EF5350", "white"),
            "warning": ("#FFA726", "white"),
            "default": ("#3D3D3D", "#F0F0F0")
        }
        current_color_map = COLOR_MAP_DARK if is_dark else COLOR_MAP_LIGHT

        # Base QSS for all buttons, as per user feedback
        BASE_BUTTON_QSS = """
            QPushButton {{
                border: none;
                border-radius: 6px; /* User suggestion */
                font-size: 16px;    /* User suggestion */
                font-weight: 600;   /* User suggestion */
                min-height: 42px;   /* User suggestion */
            }}
            QPushButton:hover {{ filter: brightness(1.08); }}
            QPushButton:pressed {{ filter: brightness(0.92); }}
        """
        # This base QSS will be applied to the parent, and specific colors per button
        # For simplicity, we will apply directly to each button for now.

        frame_style = f"background-color: {bg_color}; border-radius: 6px; padding: 8px;" # Increased padding
        # display_frame_style = frame_style # Display frame can use the same general frame style
        
        # Card styles for outer frames
        card_bg_color = QColor(bg_color).lighter(103).name() if is_dark else QColor(bg_color).darker(103).name()
        card_border_color = QColor(border_color).lighter(110).name() if is_dark else QColor(border_color).darker(110).name()
        
        # More distinct card background for light theme, subtle for dark
        actual_card_bg = QColor(Qt.GlobalColor.white).name() if not is_dark else QColor("#2E2E2E").name() # Example dark card bg
        actual_card_border = "#D0D0D0" if not is_dark else "#404040" # Example dark card border
        
        card_qss = f"""
            QWidget {{
                background-color: {actual_card_bg};
                border-radius: 8px; /* Slightly more rounded */
                border: 1px solid {actual_card_border};
                /* For shadow, QGraphicsDropShadowEffect is better, QSS shadow is limited */
                /* Example: 'box-shadow: 2px 2px 5px rgba(0,0,0,0.1);' - Not standard QSS */
            }}
        """
        # Apply card style to the new outer frames
        outer_display = self.findChild(QWidget, "calcOuterDisplayFrame")
        if outer_display: outer_display.setStyleSheet(card_qss + "padding: 8px;") # Add padding to the card

        outer_std_buttons = self.findChild(QWidget, "calcOuterStdButtonsFrame")
        if outer_std_buttons: outer_std_buttons.setStyleSheet(card_qss + "padding: 8px;")

        outer_sci_buttons = self.findChild(QWidget, "calcOuterSciButtonsFrame")
        if outer_sci_buttons: outer_sci_buttons.setStyleSheet(card_qss + "padding: 8px;")
        
        outer_expr_buttons = self.findChild(QWidget, "calcOuterExprButtonsFrame")
        if outer_expr_buttons: outer_expr_buttons.setStyleSheet(card_qss + "padding: 8px;")


        # Style for mode_frame (the container of mode buttons) - should be less prominent than cards
        mode_frame_widget = self.findChild(QWidget, "calcModeFrame")
        if mode_frame_widget:
            mode_frame_widget.setStyleSheet(f"background-color: transparent; border: none; border-radius: 6px; padding: 0px; margin-bottom: 5px;")


        self.display.setStyleSheet(
            f"border: none; background-color: {display_bg}; color: {text_color}; padding: 6px 12px 6px 12px; " # User suggested padding
            f"font-family: 'SF Mono', 'Consolas'; font-size: 28px;" # User suggested font
        )
        self.history_display.setStyleSheet(f"color: {history_text_color}; margin-bottom: 2px; background-color: transparent; padding-right: 12px;")

        # Checkbox styling is removed as they are replaced by mode buttons
        # self._apply_common_checkbox_style is also removed/obsolete

        # Styling for mode buttons (QPushButtons styled as segmented buttons)
        mode_btn_qss_parts = []
        mode_button_names = ["标准", "科学", "表达式"]
        for i, mode_text in enumerate(mode_button_names):
            object_name = f"modeButton{mode_text.replace(' ', '')}"
            
            # Base style for each mode button
            mode_btn_style = f"""
                QPushButton#{object_name} {{
                    border: 1px solid {border_color};
                    background: {QColor(bg_color).lighter(105).name()};
                    color: {text_color};
                    padding: 7px 10px; /* Adjusted padding */
                    min-height: 30px; /* Adjusted height */
                    font-size: 13px; /* Adjusted font size */
                }}
                QPushButton#{object_name}:hover:!checked {{
                    background: {QColor(bg_color).lighter(115).name()};
                }}
                QPushButton#{object_name}:checked {{
                    background: {current_color_map['op_primary'][0]};
                    color: {current_color_map['op_primary'][1]};
                    border-color: {current_color_map['op_primary'][0]};
                }}
            """
            # Adjust borders for segmented look
            if i == 0: # First button
                mode_btn_style += f"QPushButton#{object_name} {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; border-right-width: 0px; }}"
            elif i == len(mode_button_names) - 1: # Last button
                mode_btn_style += f"QPushButton#{object_name} {{ border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}"
            else: # Middle buttons
                mode_btn_style += f"QPushButton#{object_name} {{ border-radius: 0px; border-right-width: 0px; }}"
            
            mode_btn_qss_parts.append(mode_btn_style)
        
        # Apply mode button styles directly to each button
        for mode_text, button_widget in self.mode_buttons.items():
            # Construct the specific QSS for this button based on its position
            idx = mode_button_names.index(mode_text)
            temp_qss = f"""
                QPushButton#{button_widget.objectName()} {{
                    border: 1px solid {border_color};
                    background: {QColor(bg_color).lighter(105).name()};
                    color: {text_color};
                    padding: 7px 10px;
                    min-height: 30px;
                    font-size: 13px;
                    {'border-top-left-radius: 6px; border-bottom-left-radius: 6px; border-right-width: 0px;' if idx == 0 else ''}
                    {'border-top-right-radius: 6px; border-bottom-right-radius: 6px;' if idx == len(mode_button_names) - 1 else ('' if idx == 0 else 'border-radius: 0px; border-right-width: 0px;')}
                }}
                QPushButton#{button_widget.objectName()}:hover:!checked {{
                    background: {QColor(bg_color).lighter(115).name()};
                }}
                QPushButton#{button_widget.objectName()}:checked {{
                    background: {current_color_map['op_primary'][0]};
                    color: {current_color_map['op_primary'][1]};
                    border-color: {current_color_map['op_primary'][0]};
                }}
            """
            button_widget.setStyleSheet(temp_qss)


        # Update button styles using COLOR_MAP
        # Iterate over all buttons collected in _create_buttons and expression mode buttons
        all_calc_buttons = getattr(self, '_all_calculator_buttons', [])
        expr_mode_buttons = self.expression_calculator.findChildren(QPushButton) if hasattr(self, 'expression_calculator') else []
        
        processed_buttons = set()

        for button in all_calc_buttons + expr_mode_buttons:
            if button in processed_buttons:
                continue
            processed_buttons.add(button)

            text = button.text()
            category = "default" # Default category

            # Categorize buttons for styling (Standard and Scientific)
            if text.isdigit() or text == '.':
                category = "digit"
            elif text in ['÷', '×', '-', '+', '=']:
                category = "op_primary"
            elif text in ['sin', 'cos', 'tan', 'x²', 'x³', 'xʸ', '√', 'ln', 'log', '1/x', 'π', 'e']: # Sci ops
                category = "op_secondary"
            elif text == 'C':
                category = "danger"
            elif text in ['⌫', '±']:
                category = "warning"
            
            # Categorize Expression mode buttons
            if self.mode_buttons["表达式"].isChecked() and button in expr_mode_buttons: # Updated check
                 if text in ['sin','cos','tan','ln','log','asin','acos','atan','exp','sqrt','pi','e','phi','c','g']:
                     category = "op_secondary"
                 elif text in ['(',')','+','-','*','/','^','%',',']:
                     category = "op_primary" # Or a new category like "op_expr"
                 elif text == '=':
                     category = "op_primary"
                 elif text == '清除':
                     category = "danger"
                 elif text == 'Help' or text.endswith('→') or text.startswith('convert'):
                     category = "warning"


            btn_bg, btn_text_color = current_color_map.get(category, current_color_map["default"])
            
            # Use BASE_BUTTON_QSS and append specific colors
            # Note: QSS filter property is not standard, hover/pressed are better handled by pseudo-states
            specific_button_qss = (
                f"QPushButton {{"
                f"background-color: {btn_bg};"
                f"color: {btn_text_color};"
                f"border: none;"
                f"border-radius: 6px;"
                f"font-size: 16px;"
                f"font-weight: 600;"
                f"min-height: 42px;"
                f"}}"
                f"QPushButton:hover {{"
                # f"background-color: {self.adjust_qcolor(QColor(btn_bg), 1.08).name()};" # Adjust brightness
                f"background-color: {QColor(btn_bg).lighter(108).name()};" # Lighter shade for hover
                f"}}"
                f"QPushButton:pressed {{"
                # f"background-color: {self.adjust_qcolor(QColor(btn_bg), 0.92).name()};" # Adjust brightness
                f"background-color: {QColor(btn_bg).darker(108).name()};" # Darker shade for pressed
                f"}}"
            )
            button.setStyleSheet(specific_button_qss)
            
    @staticmethod
    def adjust_qcolor(color: QColor, factor: float) -> QColor:
        """Adjusts QColor brightness by a factor."""
        h, s, l, a = color.getHslF()
        l = max(0.0, min(1.0, l * factor))
        return QColor.fromHslF(h, s, l, a)

    # --- Helper Styling Methods ---
    def _apply_common_frame_style(self, widgets):
        # This method is now OBSOLETE as QSS in update_styles handles frame styling
        pass
        # style = "background-color: rgba(240, 240, 240, 0.7); border-radius: 6px; padding: 5px;"
        # for w in widgets: w.setStyleSheet(style)

    def _apply_common_checkbox_style(self, checkboxes):
        # This method is now OBSOLETE as checkboxes are replaced by mode buttons
        pass
        # style = """
        #     QCheckBox { font-size: 12px; padding: 3px; background-color: transparent; }
        # """
        # for cb in checkboxes: cb.setStyleSheet(style)

    def _apply_common_button_style(self, buttons, scientific=False):
        # This method is now less relevant as styles are applied in update_styles
        # Kept for potential future use or simpler initial setup
        font_size = 16 if scientific else 18
        min_height = 40 if scientific else 50
        style = f"""
            QPushButton {{
                min-height: {min_height}px;
                font-size: {font_size}px;
                font-weight: bold;
                border-radius: 6px;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                color: #2c3e50; /* Default text color */
            }}
            QPushButton:hover {{ background-color: #d6dbdf; }}
            QPushButton:pressed {{ background-color: #bdc3c7; }}
        """
        # Apply base style, specific colors handled in update_styles
        for btn in buttons:
            btn.setStyleSheet(style)


    # --- Calculator Logic (mostly unchanged, adapted for widget context) ---
    # def switch_calculator_mode(self, checked): # Old method, to be removed
    #     if checked:
    #         sender = self.sender()
    #         # ...
    
    def switch_calculator_mode_by_id(self, button_id: int):
        """Switches calculator mode based on the ID of the button clicked in the mode_button_group."""
        current_theme_is_dark = False # Default, will be updated if theme_manager exists
        if hasattr(self, 'theme_manager') and self.theme_manager:
            current_theme_is_dark = self.theme_manager.is_dark_theme()
        elif hasattr(self.parent(), 'theme_manager') and self.parent().theme_manager: # Check parent
            current_theme_is_dark = self.parent().theme_manager.is_dark_theme()


        if button_id == 0:  # 标准
            self.stacked_widget.setCurrentIndex(0)
            self.display.setReadOnly(True)
            # self.mode_buttons["标准"].setChecked(True) # Button group handles exclusive check
        elif button_id == 1:  # 科学
            self.stacked_widget.setCurrentIndex(1)
            self.display.setReadOnly(True)
            # self.mode_buttons["科学"].setChecked(True)
        elif button_id == 2:  # 表达式
            self.stacked_widget.setCurrentIndex(2)
            self.display.setReadOnly(False)
            self.display.setFocus()
            # self.mode_buttons["表达式"].setChecked(True)
        
        self.adjustSize()  # Adjust size after mode switch
        self.reset_calculator()  # Reset state when switching modes
        # Re-apply styles to ensure :checked pseudo-state is updated correctly for the mode buttons
        self.update_styles(is_dark=current_theme_is_dark)


    def button_clicked(self):
        # Standard/Scientific button logic
        sender = self.sender()
        text = sender.text()

        if text == 'C': self.reset_calculator()
        elif text == '⌫': self.backspace()
        elif text == '±': self.negate()
        elif text == '=': self.calculate_result()
        elif text in ['+', '-', '×', '÷', 'xʸ']: self.set_operator(text)
        elif text == '.': self.add_decimal_point()
        elif text in ['sin', 'cos', 'tan', 'sqrt', '√', 'ln', 'log', '1/x', 'x²', 'x³']: self.apply_function(text)
        elif text == 'π': self.add_constant(math.pi)
        elif text == 'e': self.add_constant(math.e)
        elif text == '(' or text == ')': self.add_bracket(text) # Basic bracket handling
        else: self.add_digit(text) # Assume digit

    def reset_calculator(self):
        self.display.setText("0")
        self.history_display.setText("")
        self.current_op = ""
        self.first_number = 0.0 # Use float
        self.new_number = True
        self.last_button_was_equal = False
        self.brackets_count = 0 # Basic bracket tracking

    def backspace(self):
        if self.display.isReadOnly(): # Only for standard/scientific
            current = self.display.text()
            if len(current) > 1: self.display.setText(current[:-1])
            else: self.reset_calculator() # Reset if only one digit left
        else: # Expression mode uses standard QLineEdit backspace
             self.display.backspace()


    def negate(self):
        current = self.display.text()
        try:
            val = float(current)
            if val != 0:
                self.display.setText(str(-val if val != int(val) else int(-val)))
                self.new_number = False # Negating doesn't start a new number
        except ValueError:
            pass # Ignore if display is not a valid number

    def add_decimal_point(self):
        current = self.display.text()
        if '.' not in current:
            if self.new_number:
                self.display.setText("0.")
                self.new_number = False
            else:
                self.display.setText(current + ".")

    def add_digit(self, digit):
        current = self.display.text()
        # Prevent leading zeros unless it's the only digit
        if self.new_number or current == "0":
            self.display.setText(digit)
            self.new_number = False
        else:
            self.display.setText(current + digit)

    def set_operator(self, operator):
        try:
            if not self.new_number and self.current_op and not self.last_button_was_equal:
                self.calculate_result() # Calculate previous operation first
                if "错误" in self.display.text(): return # Stop if calculation failed

            self.first_number = float(self.display.text())
            self.current_op = operator
            op_display = operator if operator != 'xʸ' else '^'
            self.history_display.setText(f"{self._format_number(self.first_number)} {op_display}")
            self.new_number = True
            self.last_button_was_equal = False
        except ValueError:
            self.display.setText("错误")
            self.new_number = True
        except Exception as e:
            self.display.setText("错误")
            self.new_number = True
            print(f"Error setting operator: {e}")


    def calculate_result(self):
        if self.new_number and not self.last_button_was_equal: # Prevent calculation if no second number entered
             return
        if not self.current_op: # Prevent calculation if no operator set
             return

        try:
            second_number = float(self.display.text())
            first_num_str = self._format_number(self.first_number)
            second_num_str = self._format_number(second_number)
            op_display = self.current_op if self.current_op != 'xʸ' else '^'

            if not self.last_button_was_equal: # Update history only on first '=' press
                 self.history_display.setText(f"{first_num_str} {op_display} {second_num_str} =")

            result = 0.0
            if self.current_op == '+': result = self.first_number + second_number
            elif self.current_op == '-': result = self.first_number - second_number
            elif self.current_op == '×': result = self.first_number * second_number
            elif self.current_op == '÷':
                if second_number == 0: raise ZeroDivisionError("除数不能为零")
                result = self.first_number / second_number
            elif self.current_op == 'xʸ': result = self.first_number ** second_number
            else: result = second_number # Should not happen

            result_str = self._format_number(result)
            self.display.setText(result_str)

            # Prepare for potential chained calculation
            self.first_number = result # Store result for next operation
            # Keep self.current_op and second_number for repeated '=' presses
            self.last_button_was_equal = True
            self.new_number = True # Ready for new input or another '='

        except ZeroDivisionError as e:
            self.display.setText(str(e))
            self.new_number = True
            self.last_button_was_equal = False
        except ValueError:
            self.display.setText("输入错误")
            self.new_number = True
            self.last_button_was_equal = False
        except Exception as e:
            self.display.setText("计算错误")
            self.new_number = True
            self.last_button_was_equal = False
            print(f"Calculation error: {e}")

    def apply_function(self, function):
        try:
            value = float(self.display.text())
            result = 0.0
            func_display = ""

            if function in ['sin', 'cos', 'tan']:
                # Assume input is in degrees for user convenience, convert to radians
                val_rad = math.radians(value)
                if function == 'sin': result = math.sin(val_rad)
                elif function == 'cos': result = math.cos(val_rad)
                elif function == 'tan':
                     # Avoid tan(90), tan(270) etc.
                     if math.isclose((value % 180), 90): raise ValueError("tan(90k) 无定义")
                     result = math.tan(val_rad)
                func_display = f"{function}({self._format_number(value)}°)"
            elif function == 'ln':
                if value <= 0: raise ValueError("ln(x) x需>0")
                result = math.log(value)
                func_display = f"ln({self._format_number(value)})"
            elif function == 'log':
                if value <= 0: raise ValueError("log(x) x需>0")
                result = math.log10(value)
                func_display = f"log({self._format_number(value)})"
            elif function in ['√', 'sqrt']:
                if value < 0: raise ValueError("负数不能开平方")
                result = math.sqrt(value)
                func_display = f"√({self._format_number(value)})"
            elif function == 'x²':
                result = value ** 2
                func_display = f"({self._format_number(value)})²"
            elif function == 'x³':
                result = value ** 3
                func_display = f"({self._format_number(value)})³"
            elif function == '1/x':
                if value == 0: raise ZeroDivisionError("除数不能为零")
                result = 1 / value
                func_display = f"1/({self._format_number(value)})"
            else: raise ValueError("未知函数")

            self.history_display.setText(f"{func_display} =")
            result_str = self._format_number(result)
            self.display.setText(result_str)
            self.first_number = result # Store result
            self.last_button_was_equal = True
            self.new_number = True

        except ValueError as e:
            self.display.setText(str(e))
            self.new_number = True
            self.last_button_was_equal = False
        except ZeroDivisionError as e:
            self.display.setText(str(e))
            self.new_number = True
            self.last_button_was_equal = False
        except Exception as e:
            self.display.setText("计算错误")
            self.new_number = True
            self.last_button_was_equal = False
            print(f"Function error: {e}")

    def add_constant(self, value):
        self.display.setText(self._format_number(value))
        self.new_number = True
        self.last_button_was_equal = False # Adding constant resets '=' chain

    def add_bracket(self, bracket):
        # Basic bracket handling for display, not full parsing in std/sci mode
        current = self.display.text()
        if self.new_number or current == "0":
            if bracket == '(':
                self.display.setText('(')
                self.brackets_count += 1
                self.new_number = False # Start entering number inside bracket
            # Don't add closing bracket on new number
        else:
            if bracket == '(':
                 # Implicit multiplication maybe? Or just append? Append for now.
                 self.display.setText(current + '(')
                 self.brackets_count += 1
            elif bracket == ')' and self.brackets_count > 0:
                 self.display.setText(current + ')')
                 self.brackets_count -= 1
            # Ignore closing bracket if no opening one

    def _format_number(self, num):
        """Format number, removing trailing .0"""
        if isinstance(num, (int, float)):
            if math.isclose(num, int(num)):
                return str(int(num))
            # Limit precision for display
            return f"{num:.10g}" # Use general format with reasonable precision
        return str(num) # Return as string if not number

    # --- Expression Mode Methods ---
    def on_display_changed(self, text):
        # Could add validation or syntax highlighting here if needed
        pass

    def insert_function(self, function_name):
        if self.expression_mode.isChecked():
            self.display.insert(f"{function_name}(")
            self.display.setFocus()

    def insert_text(self, text):
        if self.expression_mode.isChecked():
            self.display.insert(text)
            self.display.setFocus()

    def insert_unit_conversion(self, unit_code):
        if self.expression_mode.isChecked():
            self.display.insert(f"convert(,{unit_code})")
            self.display.cursorBackward(False, len(unit_code) + 2) # Move cursor before comma
            self.display.setFocus()

    def calculate_expression(self):
        if self.expression_mode.isChecked():
            expression = self.display.text()
            self.history_display.setText(f"{expression} =")
            try:
                result = self.evaluator.evaluate(expression)
                result_str = self._format_number(result)
                self.display.setText(result_str)
            except Exception as e:
                self.display.setText(f"错误") # Keep error short
                self.history_display.setText(f"{expression} = {e}") # Show error in history
            self.display.selectAll() # Select result for easy copying/overwriting
            self.display.setFocus()

    def show_expression_help(self):
        help_text = """
表达式模式帮助:
- 函数: sin(), cos(), tan(), asin(), acos(), atan(), sqrt(), log() (base 10), ln() (natural), exp(), abs(), round(), floor(), ceil(), rad(), deg()
- 常量: pi, e, phi (黄金分割), c (光速), g (重力加速度)
- 运算符: +, -, *, /, ^ (幂), % (取模)
- 单位转换: convert(值, 单位代码)
  - 长度: m_to_cm, cm_to_m, m_to_km, km_to_m, m_to_in, in_to_m, m_to_ft, ft_to_m
  - 重量: kg_to_g, g_to_kg, kg_to_lb, lb_to_kg
  - 温度: c_to_f, f_to_c, c_to_k, k_to_c
示例:
  sin(pi/4)
  sqrt(16) + ln(e^2)
  convert(100, m_to_cm)
  2^10
"""
        QMessageBox.information(self, "表达式计算器帮助", help_text.strip())
