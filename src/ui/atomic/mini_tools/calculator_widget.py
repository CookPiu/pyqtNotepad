from __future__ import annotations

import math
import sys
from typing import Dict, List, Tuple

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QFont, QIcon # QIcon might be needed for backspace
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# --- local imports – keep relative path intact ---
from ...core.base_widget import BaseWidget

# ---------------------------------------------------------------------------
# 1. Helper class – expression evaluator (kept for future use in text editor)
# ---------------------------------------------------------------------------
class ExpressionEvaluator:
    """Safe(ish) evaluation of user expressions."""
    constants: Dict[str, float] = {
        "pi": math.pi, "e": math.e, "phi": (1 + math.sqrt(5)) / 2,
        "c": 299_792_458, "g": 9.80665,
    }
    functions: Dict[str, object] = {
        "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin,
        "acos": math.acos, "atan": math.atan, "sqrt": math.sqrt, "log": math.log10,
        "ln": math.log, "abs": abs, "exp": math.exp, "rad": math.radians,
        "deg": math.degrees, "round": round, "floor": math.floor, "ceil": math.ceil,
    }
    def evaluate(self, expression: str):
        try:
            safe_globals: Dict[str, object] = {"__builtins__": {}}
            safe_locals = {**self.constants, **self.functions}
            expression = expression.replace("×", "*").replace("÷", "/").replace("^", "**").replace("π", "pi")
            return eval(expression, safe_globals, safe_locals)
        except Exception as e:
            raise ValueError(str(e)) from None

# ---------------------------------------------------------------------------
# 2. UI utilities – role‑based button
# ---------------------------------------------------------------------------
class CalcButton(QPushButton):
    """Small helper to tag buttons with semantic *role* for styling."""
    def __init__(self, text: str, role: str = "digit", parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setProperty("role", role)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFont(QFont("Segoe UI", 14)) # Default font size for buttons

# ---------------------------------------------------------------------------
# 3. Main widget
# ---------------------------------------------------------------------------
class CalculatorWidget(BaseWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.evaluator = ExpressionEvaluator() # Kept for potential future use
        self.reset_calculator()
        self.setObjectName("CalculatorWidget")

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(10)

        # --- Display Area ---
        display_card = QWidget(objectName="displayCard")
        display_layout = QVBoxLayout(display_card)
        display_layout.setContentsMargins(12, 12, 12, 12)
        display_layout.setSpacing(0)

        self.history_display = QLabel("", alignment=Qt.AlignmentFlag.AlignRight)
        self.history_display.setObjectName("historyDisplay")
        self.history_display.setMinimumHeight(20)
        display_layout.addWidget(self.history_display)

        self.main_display = QLineEdit("0", readOnly=True)
        self.main_display.setObjectName("mainDisplay")
        self.main_display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.main_display.setMinimumHeight(60) # Increased height for larger font
        display_layout.addWidget(self.main_display)
        
        root_layout.addWidget(display_card)

        # --- Buttons Panel ---
        buttons_panel = self._build_buttons_panel()
        root_layout.addWidget(buttons_panel)

        self.update_styles()

    def _build_buttons_panel(self) -> QWidget:
        panel = QWidget()
        grid_layout = QGridLayout(panel)
        grid_layout.setSpacing(6) # Spacing between buttons

        # Button definitions: (text, role, grid_row, grid_col, row_span, col_span)
        # Roles: 'digit', 'op' (binary), 'func' (unary), 'clear', 'equal'
        button_definitions: List[Tuple[str, str, int, int, int, int]] = [
            ("%", "func", 0, 0, 1, 1), ("CE", "clear", 0, 1, 1, 1),
            ("C", "clear", 0, 2, 1, 1), ("⌫", "clear", 0, 3, 1, 1),

            ("¹/x", "func", 1, 0, 1, 1), ("x²", "func", 1, 1, 1, 1),
            ("²√x", "func", 1, 2, 1, 1), ("÷", "op", 1, 3, 1, 1),

            ("7", "digit", 2, 0, 1, 1), ("8", "digit", 2, 1, 1, 1),
            ("9", "digit", 2, 2, 1, 1), ("×", "op", 2, 3, 1, 1),

            ("4", "digit", 3, 0, 1, 1), ("5", "digit", 3, 1, 1, 1),
            ("6", "digit", 3, 2, 1, 1), ("-", "op", 3, 3, 1, 1),

            ("1", "digit", 4, 0, 1, 1), ("2", "digit", 4, 1, 1, 1),
            ("3", "digit", 4, 2, 1, 1), ("+", "op", 4, 3, 1, 1),

            ("+/-", "func", 5, 0, 1, 1), ("0", "digit", 5, 1, 1, 1),
            (".", "digit", 5, 2, 1, 1), ("=", "equal", 5, 3, 1, 1),
        ]

        for text, role, r, c, rs, cs in button_definitions:
            button = CalcButton(text, role)
            button.clicked.connect(self._on_button_click)
            grid_layout.addWidget(button, r, c, rs, cs)
        
        return panel

    def update_styles(self, is_dark: bool = False): # Add is_dark parameter
        # Define colors based on theme
        if is_dark:
            bg_color = "#2E2E2E"
            display_card_bg_color = "#2E2E2E"
            main_display_text_color = "#E0E0E0"
            history_display_text_color = "#AAAAAA"
            button_border_color = "#454545"
            digit_button_bg = "#3C3C3C"
            digit_button_text = "#E0E0E0"
            digit_button_hover_bg = "#4A4A4A"
            op_button_bg = "#353535"
            op_button_text = "#E0E0E0"
            op_button_hover_bg = "#424242"
            clear_button_bg = "#353535"
            clear_button_text = "#E0E0E0"
            clear_button_hover_bg = "#424242"
            equal_button_bg = "#0A84FF" # Blue for equals
            equal_button_text = "#FFFFFF"
            equal_button_hover_bg = "#0070D9"
            pressed_button_bg = "#505050"
        else: # Light theme (original colors)
            bg_color = "#F0E8F3"
            display_card_bg_color = "#F0E8F3"
            main_display_text_color = "#000000"
            history_display_text_color = "#555555"
            button_border_color = "#D0D0D0"
            digit_button_bg = "#FFFFFF"
            digit_button_text = "#000000"
            digit_button_hover_bg = "#F0F0F0"
            op_button_bg = "#F8F8F8"
            op_button_text = "#333333"
            op_button_hover_bg = "#E8E8E8"
            clear_button_bg = "#F8F8F8"
            clear_button_text = "#333333"
            clear_button_hover_bg = "#E8E8E8"
            equal_button_bg = "#333333"
            equal_button_text = "#FFFFFF"
            equal_button_hover_bg = "#454545"
            pressed_button_bg = "#D0D0D0"

        # Overall widget style (background)
        self.setStyleSheet(f"""
            CalculatorWidget {{
                background-color: {bg_color};
            }}
            #displayCard {{
                background-color: {display_card_bg_color};
                border: none;
                border-radius: 8px;
            }}
            #mainDisplay {{
                background-color: {display_card_bg_color}; 
                border: none; 
                color: {main_display_text_color};
                font-family: 'Segoe UI';
                font-size: 40px; 
                font-weight: bold;
                padding: 5px;
            }}
            #historyDisplay {{
                background-color: {display_card_bg_color};
                color: {history_display_text_color};
                font-family: 'Segoe UI';
                font-size: 14px;
                padding-right: 5px;
            }}
        """)

        button_base_style = f"""
            QPushButton {{
                border: 1px solid {button_border_color};
                border-radius: 6px;
                font-family: 'Segoe UI';
                font-size: 15px;
                min-height: 40px; 
            }}
            QPushButton:hover {{
                border: 1px solid {self._adjust_border_color(button_border_color, is_dark)};
            }}
            QPushButton:pressed {{
                background-color: {pressed_button_bg};
            }}
        """
        
        for btn in self.findChildren(CalcButton):
            role = btn.property("role")
            current_style = button_base_style # Start with base
            
            specific_style = ""
            if role == "digit" or role == "func" or role == "clear":
                if btn.text() in ["CE", "C", "⌫"] or btn.text() in ["¹/x", "x²", "²√x", "%", "+/-"]:
                    specific_style = f"""
                        QPushButton {{ background-color: {clear_button_bg}; color: {clear_button_text}; }}
                        QPushButton:hover {{ background-color: {clear_button_hover_bg}; }}
                    """
                else: # Digits and dot
                    specific_style = f"""
                        QPushButton {{ background-color: {digit_button_bg}; color: {digit_button_text}; font-weight: 600; font-size: 16px;}}
                        QPushButton:hover {{ background-color: {digit_button_hover_bg}; }}
                    """
            elif role == "op":
                specific_style = f"""
                    QPushButton {{ background-color: {op_button_bg}; color: {op_button_text}; font-size: 18px;}}
                    QPushButton:hover {{ background-color: {op_button_hover_bg}; }}
                """
            elif role == "equal":
                specific_style = f"""
                    QPushButton {{ background-color: {equal_button_bg}; color: {equal_button_text}; font-size: 18px; font-weight: bold;}}
                    QPushButton:hover {{ background-color: {equal_button_hover_bg}; }}
                    QPushButton:pressed {{ background-color: {self._adjust_button_pressed_color(equal_button_bg, is_dark)}; }}
                """
            btn.setStyleSheet(current_style + specific_style)

    def _adjust_border_color(self, color_hex, is_dark_theme, amount=20):
        # Simple helper to darken/lighten border for hover
        # This is a placeholder, a more robust QColor based adjustment would be better
        if is_dark_theme: # lighten
            return self._adjust_hex_color(color_hex, amount)
        else: # darken
            return self._adjust_hex_color(color_hex, -amount)

    def _adjust_button_pressed_color(self, color_hex, is_dark_theme, amount=20):
        if is_dark_theme: # darken further
            return self._adjust_hex_color(color_hex, -amount)
        else: # darken
            return self._adjust_hex_color(color_hex, -amount) # Or use a fixed pressed_button_bg

    def _adjust_hex_color(self, hex_str, change):
        try:
            hex_val = hex_str.lstrip('#')
            lv = len(hex_val)
            rgb = tuple(int(hex_val[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
            new_rgb = tuple(max(0, min(255, val + change)) for val in rgb)
            return f"#{''.join([f'{val:02x}' for val in new_rgb])}"
        except:
            return hex_str # fallback

    def reset_calculator(self):
        self.current_input = "0"
        self.first_operand = None
        self.pending_operation = None
        self.waiting_for_second_operand = False
        self.history_text = ""
        self._update_display()

    def _update_display(self):
        self.main_display.setText(self.current_input if self.current_input else "0")
        self.history_display.setText(self.history_text)
        # Limit display length to prevent overflow visually
        if len(self.main_display.text()) > 15: # Arbitrary limit
            self.main_display.setText(self.main_display.text()[:15]+"...")


    def _on_button_click(self):
        button = self.sender()
        text = button.text()
        role = button.property("role")

        if role == "digit":
            self._append_digit(text)
        elif role == "op":
            self._handle_operation(text)
        elif role == "func":
            self._handle_function(text)
        elif role == "clear":
            self._handle_clear(text)
        elif role == "equal":
            self._calculate_result()
        
        self._update_display()

    def _append_digit(self, digit: str):
        if self.waiting_for_second_operand:
            self.current_input = digit
            self.waiting_for_second_operand = False
        elif self.current_input == "0" and digit != ".":
            self.current_input = digit
        elif digit == "." and "." in self.current_input:
            return # Avoid multiple dots
        else:
            if len(self.current_input) < 16: # Limit input length
                 self.current_input += digit
        self.last_action_was_operator = False


    def _handle_operation(self, op_symbol: str):
        try:
            current_value = float(self.current_input)
        except ValueError:
            self.current_input = "错误"
            self.history_text = ""
            return

        if self.pending_operation and not self.waiting_for_second_operand:
            self._calculate_result(is_intermediate_calc=True)
            # After an intermediate calculation, the result becomes the new first_operand
            try:
                self.first_operand = float(self.current_input)
            except ValueError: # Result was "Error"
                self.reset_calculator()
                self.current_input = "错误"
                return
        else:
            self.first_operand = current_value
        
        self.pending_operation = op_symbol
        self.waiting_for_second_operand = True
        self.history_text = f"{self.first_operand:g} {op_symbol}"
        self.last_action_was_operator = True


    def _calculate_result(self, is_intermediate_calc=False):
        if self.pending_operation is None or self.first_operand is None:
            return
        
        try:
            second_operand = float(self.current_input)
        except ValueError:
            self.current_input = "错误"
            self.history_text = ""
            return

        result = 0.0
        op = self.pending_operation
        error = None

        if op == "+": result = self.first_operand + second_operand
        elif op == "-": result = self.first_operand - second_operand
        elif op == "×": result = self.first_operand * second_operand
        elif op == "÷":
            if second_operand == 0: error = "除数不能为零"
            else: result = self.first_operand / second_operand
        
        if error:
            self.current_input = error
            if not is_intermediate_calc:
                self.history_text = "" # Clear history on final error
        else:
            # Format result: remove .0 for whole numbers
            if result == int(result): result_str = str(int(result))
            else: result_str = f"{result:g}" # Use general format for floats
            
            self.current_input = result_str
            if not is_intermediate_calc:
                 self.history_text = f"{self.first_operand:g} {op} {second_operand:g} ="
                 self.pending_operation = None # Clear operation after final equals
                 self.first_operand = None # Clear first operand
            else: # For intermediate calculation, result becomes first_operand for next op
                 self.first_operand = result 
                 # history_text is already set by _handle_operation for the *next* op

        self.waiting_for_second_operand = True # Ready for new number or new op
        if not is_intermediate_calc:
            self.last_action_was_operator = False # After '=', can start new number


    def _handle_function(self, func_symbol: str):
        try:
            value = float(self.current_input)
        except ValueError:
            self.current_input = "错误"
            return

        result = value
        error = None
        original_value_str = f"{value:g}" # For history

        if func_symbol == "+/-": result = -value
        elif func_symbol == "%":
            if self.first_operand is not None and self.pending_operation:
                # Calculate B% of A, e.g., A + B% = A + (A * B/100)
                # Here, we just calculate the B% part. The operation handles the rest.
                result = self.first_operand * (value / 100)
            else: # Standalone percentage
                result = value / 100
        elif func_symbol == "¹/x":
            if value == 0: error = "除数不能为零"
            else: result = 1 / value
        elif func_symbol == "x²": result = value ** 2
        elif func_symbol == "²√x":
            if value < 0: error = "无效输入" # Sqrt of negative
            else: result = math.sqrt(value)
        
        if error:
            self.current_input = error
        else:
            if result == int(result): self.current_input = str(int(result))
            else: self.current_input = f"{result:g}"
        
        # Update history for unary operations if needed, or let display show it
        # For now, unary ops directly change current_input. History might not reflect func(val)
        # self.history_text = f"{func_symbol}({original_value_str})" # Optional: show unary op in history
        
        self.waiting_for_second_operand = False # After a function, can continue typing or op
        self.last_action_was_operator = False


    def _handle_clear(self, clear_type: str):
        if clear_type == "C":
            self.reset_calculator()
        elif clear_type == "CE": # Clear current entry
            self.current_input = "0"
            if self.waiting_for_second_operand:
                # If we were waiting for a second operand, CE clears that input
                # but doesn't affect the first_operand or pending_operation
                pass 
            else:
                # If CE is pressed on the first number, or after '=', it's like 'C' for current input
                # but doesn't clear history if an operation was set.
                # This behavior can be nuanced. For simplicity:
                pass
            self.waiting_for_second_operand = self.pending_operation is not None

        elif clear_type == "⌫": # Backspace
            if self.waiting_for_second_operand: # Don't backspace if an op was just pressed
                return
            if len(self.current_input) > 1:
                self.current_input = self.current_input[:-1]
            elif self.current_input != "0":
                self.current_input = "0"
        
        self.last_action_was_operator = False


# ---------------------------------------------------------------------------
#  Debug / standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Apply a basic style for standalone testing if needed
    # app.setStyleSheet("QWidget { font-family: 'Segoe UI'; }")
    
    window = QWidget()
    window.setWindowTitle("Calculator Test")
    layout = QVBoxLayout(window)
    calc_widget = CalculatorWidget()
    layout.addWidget(calc_widget)
    window.resize(320, 500) # Approximate size
    window.show()
    
    sys.exit(app.exec())
