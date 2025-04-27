import sys
import math
import re
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGridLayout, QLineEdit, QApplication,
                             QStackedWidget, QCheckBox, QButtonGroup, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon
from src.utils.theme_manager import ThemeManager


class ExpressionEvaluator:
    """表达式计算器类，实现简单的表达式解析和计算"""
    
    def __init__(self):
        # 定义常量
        self.constants = {
            'pi': math.pi,
            'e': math.e,
            'phi': (1 + math.sqrt(5)) / 2,  # 黄金比例
            'c': 299792458,  # 光速 (m/s)
            'g': 9.80665,  # 重力加速度 (m/s²)
        }
        
        # 定义数学函数
        self.functions = {
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'sqrt': math.sqrt,
            'log': math.log10,
            'ln': math.log,
            'abs': abs,
            'exp': math.exp,
            'rad': math.radians,
            'deg': math.degrees,
            'round': round,
            'floor': math.floor,
            'ceil': math.ceil,
        }
        
        # 定义简单单位转换
        self.units = {
            # 长度
            'm_to_cm': lambda x: x * 100,  # 米到厘米
            'cm_to_m': lambda x: x / 100,  # 厘米到米
            'm_to_km': lambda x: x / 1000,  # 米到千米
            'km_to_m': lambda x: x * 1000,  # 千米到米
            'm_to_in': lambda x: x * 39.3701,  # 米到英寸
            'in_to_m': lambda x: x / 39.3701,  # 英寸到米
            'm_to_ft': lambda x: x * 3.28084,  # 米到英尺
            'ft_to_m': lambda x: x / 3.28084,  # 英尺到米
            
            # 重量/质量
            'kg_to_g': lambda x: x * 1000,  # 千克到克
            'g_to_kg': lambda x: x / 1000,  # 克到千克
            'kg_to_lb': lambda x: x * 2.20462,  # 千克到磅
            'lb_to_kg': lambda x: x / 2.20462,  # 磅到千克
            
            # 温度
            'c_to_f': lambda x: x * 9/5 + 32,  # 摄氏度到华氏度
            'f_to_c': lambda x: (x - 32) * 5/9,  # 华氏度到摄氏度
            'c_to_k': lambda x: x + 273.15,  # 摄氏度到开尔文
            'k_to_c': lambda x: x - 273.15,  # 开尔文到摄氏度
        }
    
    def evaluate(self, expression):
        """计算数学表达式的值"""
        # 替换常量
        for const_name, const_value in self.constants.items():
            expression = re.sub(r'\b' + const_name + r'\b', str(const_value), expression)
        
        # 处理函数调用
        # 匹配函数名后跟括号中的内容，如 sin(0.5)
        func_pattern = r'([a-z]+)\(([^()]+)\)'
        while re.search(func_pattern, expression):
            expression = re.sub(func_pattern, self._evaluate_function, expression)
        
        # 处理单位转换
        # 匹配单位转换格式，如 convert(5, m_to_cm)
        unit_pattern = r'convert\(([^,]+),\s*([a-z_]+)\)'
        while re.search(unit_pattern, expression):
            expression = re.sub(unit_pattern, self._convert_unit, expression)
        
        # 替换乘法和除法符号
        expression = expression.replace('×', '*').replace('÷', '/')
        
        # 安全地计算表达式
        try:
            # 使用Python内置的eval计算表达式
            # 限制访问仅可使用数学运算
            result = eval(expression, {"__builtins__": {}}, {})
            return result
        except Exception as e:
            raise ValueError(f"计算错误: {str(e)}")
    
    def _evaluate_function(self, match):
        """计算函数表达式的值"""
        func_name = match.group(1)
        arg = match.group(2)
        
        # 递归计算参数
        try:
            arg_value = self.evaluate(arg)
        except:
            # 如果无法计算，则当作数字处理
            arg_value = float(arg)
        
        if func_name in self.functions:
            try:
                return str(self.functions[func_name](arg_value))
            except Exception as e:
                raise ValueError(f"函数 {func_name} 计算错误: {str(e)}")
        else:
            raise ValueError(f"未知函数: {func_name}")
    
    def _convert_unit(self, match):
        """进行单位转换"""
        value = float(match.group(1))
        unit_converter = match.group(2)
        
        if unit_converter in self.units:
            try:
                return str(self.units[unit_converter](value))
            except Exception as e:
                raise ValueError(f"单位转换错误: {str(e)}")
        else:
            raise ValueError(f"未知单位转换: {unit_converter}")


class CalculatorWindow(QMainWindow):
    """计算器窗口，提供基本数学运算和科学计算功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager()
        
        # 初始化表达式计算器
        self.evaluator = ExpressionEvaluator()
        
        # 初始化UI
        self.initUI()
        
        # 初始化计算器状态
        self.reset_calculator()
        
        # 应用当前主题
        self.apply_current_theme()
    
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle("计算器")
        self.setGeometry(300, 300, 380, 500)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建显示部分
        display_frame = QWidget()
        display_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
            }
        """)
        display_layout = QVBoxLayout(display_frame)
        
        # 创建显示历史记录的标签
        self.history_display = QLabel("")
        self.history_display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.history_display.setFont(QFont("Arial", 12))
        self.history_display.setStyleSheet("color: #7f8c8d; margin-bottom: 5px;")
        display_layout.addWidget(self.history_display)
        
        # 创建显示当前输入的文本框
        self.display = QLineEdit("0")
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.display.setStyleSheet("""
            QLineEdit { 
                border: none; 
                background-color: transparent; 
                color: #2c3e50; 
                padding: 5px;
            }
        """)
        # 允许表达式模式下直接编辑
        self.display.textChanged.connect(self.on_display_changed)
        display_layout.addWidget(self.display)
        
        main_layout.addWidget(display_frame)
        
        # 创建切换计算器类型选项
        mode_frame = QWidget()
        mode_frame.setStyleSheet("""
            QWidget {
                background-color: rgba(240, 240, 240, 50);
                border-radius: 8px;
                padding: 5px;
            }
            QCheckBox {
                font-size: 14px;
                padding: 5px;
            }
        """)
        mode_layout = QHBoxLayout(mode_frame)
        
        # 创建单选按钮组
        self.mode_group = QButtonGroup(self)
        
        # 标准计算器选项
        self.standard_mode = QCheckBox("标准")
        self.standard_mode.toggled.connect(self.switch_calculator_mode)
        self.mode_group.addButton(self.standard_mode)
        mode_layout.addWidget(self.standard_mode)
        
        # 科学计算器选项
        self.scientific_mode = QCheckBox("科学")
        self.scientific_mode.toggled.connect(self.switch_calculator_mode)
        self.mode_group.addButton(self.scientific_mode)
        mode_layout.addWidget(self.scientific_mode)
        
        # 表达式计算器选项
        self.expression_mode = QCheckBox("表达式")
        self.expression_mode.toggled.connect(self.switch_calculator_mode)
        self.mode_group.addButton(self.expression_mode)
        mode_layout.addWidget(self.expression_mode)
        
        main_layout.addWidget(mode_frame)
        
        # 使用堆栈部件来管理不同计算器界面
        self.stacked_widget = QStackedWidget()
        
        # 标准计算器界面
        self.standard_calculator = QWidget()
        self.setup_standard_calculator()
        self.stacked_widget.addWidget(self.standard_calculator)
        
        # 科学计算器界面
        self.scientific_calculator = QWidget()
        self.setup_scientific_calculator()
        self.stacked_widget.addWidget(self.scientific_calculator)
        
        # 表达式计算器界面
        self.expression_calculator = QWidget()
        self.setup_expression_calculator()
        self.stacked_widget.addWidget(self.expression_calculator)
        
        main_layout.addWidget(self.stacked_widget)
        
        # 默认选择标准模式
        self.standard_mode.setChecked(True)
    
    def setup_standard_calculator(self):
        # 创建标准计算器布局
        layout = QVBoxLayout(self.standard_calculator)
        
        # 创建按钮布局
        buttons_frame = QWidget()
        buttons_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
            }
            QPushButton { 
                min-height: 50px; 
                font-size: 18px; 
                font-weight: bold; 
                border-radius: 8px; 
                background-color: #ecf0f1; 
                border: 1px solid #bdc3c7;
            }
            QPushButton:hover { 
                background-color: #d6dbdf; 
            }
            QPushButton:pressed { 
                background-color: #bdc3c7; 
            }
        """)
        buttons_layout = QGridLayout(buttons_frame)
        buttons_layout.setSpacing(8)
        
        # 定义按钮
        buttons = [
            ('C', 0, 0, 1, 1, '#e74c3c'), # 清除
            ('⌫', 0, 1, 1, 1, '#e67e22'), # 退格
            ('±', 0, 2, 1, 1, '#3498db'), # 正负号
            ('÷', 0, 3, 1, 1, '#3498db'), # 除法
            
            ('7', 1, 0, 1, 1, '#ecf0f1'),
            ('8', 1, 1, 1, 1, '#ecf0f1'),
            ('9', 1, 2, 1, 1, '#ecf0f1'),
            ('×', 1, 3, 1, 1, '#3498db'), # 乘法
            
            ('4', 2, 0, 1, 1, '#ecf0f1'),
            ('5', 2, 1, 1, 1, '#ecf0f1'),
            ('6', 2, 2, 1, 1, '#ecf0f1'),
            ('-', 2, 3, 1, 1, '#3498db'), # 减法
            
            ('1', 3, 0, 1, 1, '#ecf0f1'),
            ('2', 3, 1, 1, 1, '#ecf0f1'),
            ('3', 3, 2, 1, 1, '#ecf0f1'),
            ('+', 3, 3, 1, 1, '#3498db'), # 加法
            
            ('0', 4, 0, 1, 2, '#ecf0f1'), # 0占两格
            ('.', 4, 2, 1, 1, '#ecf0f1'), # 小数点
            ('=', 4, 3, 1, 1, '#2ecc71'), # 等于
        ]
        
        # 创建按钮并添加到布局
        for button_text, row, col, row_span, col_span, color in buttons:
            button = QPushButton(button_text)
            button.setStyleSheet(f"background-color: {color}; color: {'white' if color != '#ecf0f1' else '#2c3e50'};")
            button.clicked.connect(self.button_clicked)
            buttons_layout.addWidget(button, row, col, row_span, col_span)
        
        layout.addWidget(buttons_frame)
    
    def setup_scientific_calculator(self):
        # 创建科学计算器布局
        layout = QVBoxLayout(self.scientific_calculator)
        
        # 创建按钮布局
        buttons_frame = QWidget()
        buttons_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
            }
            QPushButton { 
                min-height: 40px; 
                font-size: 16px; 
                font-weight: bold; 
                border-radius: 8px; 
                background-color: #ecf0f1; 
                border: 1px solid #bdc3c7;
            }
            QPushButton:hover { 
                background-color: #d6dbdf; 
            }
            QPushButton:pressed { 
                background-color: #bdc3c7; 
            }
        """)
        buttons_layout = QGridLayout(buttons_frame)
        buttons_layout.setSpacing(8)
        
        # 定义科学计算器按钮
        buttons = [
            ('sin', 0, 0, 1, 1, '#9b59b6'),
            ('cos', 0, 1, 1, 1, '#9b59b6'),
            ('tan', 0, 2, 1, 1, '#9b59b6'),
            ('π', 0, 3, 1, 1, '#9b59b6'),
            ('e', 0, 4, 1, 1, '#9b59b6'),
            
            ('x²', 1, 0, 1, 1, '#9b59b6'),
            ('x³', 1, 1, 1, 1, '#9b59b6'),
            ('xʸ', 1, 2, 1, 1, '#9b59b6'),
            ('√', 1, 3, 1, 1, '#9b59b6'),
            ('ln', 1, 4, 1, 1, '#9b59b6'),
            
            ('(', 2, 0, 1, 1, '#3498db'),
            (')', 2, 1, 1, 1, '#3498db'),
            ('C', 2, 2, 1, 1, '#e74c3c'),
            ('⌫', 2, 3, 1, 1, '#e67e22'),
            ('÷', 2, 4, 1, 1, '#3498db'),
            
            ('7', 3, 0, 1, 1, '#ecf0f1'),
            ('8', 3, 1, 1, 1, '#ecf0f1'),
            ('9', 3, 2, 1, 1, '#ecf0f1'),
            ('×', 3, 3, 1, 1, '#3498db'),
            ('1/x', 3, 4, 1, 1, '#9b59b6'),
            
            ('4', 4, 0, 1, 1, '#ecf0f1'),
            ('5', 4, 1, 1, 1, '#ecf0f1'),
            ('6', 4, 2, 1, 1, '#ecf0f1'),
            ('-', 4, 3, 1, 1, '#3498db'),
            ('±', 4, 4, 1, 1, '#3498db'),
            
            ('1', 5, 0, 1, 1, '#ecf0f1'),
            ('2', 5, 1, 1, 1, '#ecf0f1'),
            ('3', 5, 2, 1, 1, '#ecf0f1'),
            ('+', 5, 3, 1, 1, '#3498db'),
            ('log', 5, 4, 1, 1, '#9b59b6'),
            
            ('0', 6, 0, 1, 2, '#ecf0f1'),
            ('.', 6, 2, 1, 1, '#ecf0f1'),
            ('=', 6, 3, 1, 2, '#2ecc71'),
        ]
        
        # 创建按钮并添加到布局
        for button_text, row, col, row_span, col_span, color in buttons:
            button = QPushButton(button_text)
            button.setStyleSheet(f"background-color: {color}; color: {'white' if color != '#ecf0f1' else '#2c3e50'};")
            button.clicked.connect(self.button_clicked)
            buttons_layout.addWidget(button, row, col, row_span, col_span)
        
        layout.addWidget(buttons_frame)
    
    def setup_expression_calculator(self):
        # 创建表达式计算器布局
        layout = QVBoxLayout(self.expression_calculator)
        
        # 添加输入表达式的说明
        info_label = QLabel("在表达式模式下，您可以直接在显示框中输入数学表达式，支持函数、常量和基本运算")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7f8c8d;
                padding: 5px;
                background-color: rgba(240, 240, 240, 50);
                border-radius: 5px;
            }
        """)
        layout.addWidget(info_label)
        
        # 创建按钮框架
        buttons_frame = QWidget()
        buttons_frame.setStyleSheet("""
            QWidget { 
                background-color: rgba(240, 240, 240, 50); 
                border-radius: 8px; 
                padding: 10px;
            }
            QPushButton { 
                min-height: 40px; 
                font-size: 16px; 
                font-weight: bold; 
                border-radius: 8px; 
                background-color: #ecf0f1; 
                border: 1px solid #bdc3c7;
            }
            QPushButton:hover { 
                background-color: #d6dbdf; 
            }
            QPushButton:pressed { 
                background-color: #bdc3c7; 
            }
        """)
        
        # 创建按钮布局
        buttons_layout = QGridLayout(buttons_frame)
        buttons_layout.setSpacing(8)
        
        # 数学函数按钮
        function_buttons = [
            ('sin', 0, 0), ('cos', 0, 1), ('tan', 0, 2), ('ln', 0, 3), ('log', 0, 4),
            ('asin', 1, 0), ('acos', 1, 1), ('atan', 1, 2), ('exp', 1, 3), ('sqrt', 1, 4)
        ]
        
        for func_name, row, col in function_buttons:
            button = QPushButton(func_name)
            button.setStyleSheet("background-color: #9b59b6; color: white;")
            button.clicked.connect(lambda checked, f=func_name: self.insert_function(f))
            buttons_layout.addWidget(button, row, col)
        
        # 常量按钮
        constants_label = QLabel("常量:")
        constants_label.setStyleSheet("background-color: transparent; color: #7f8c8d;")
        buttons_layout.addWidget(constants_label, 2, 0)
        
        constants = [('pi', 2, 1), ('e', 2, 2), ('phi', 2, 3), ('c', 2, 4)]
        for const_name, row, col in constants:
            button = QPushButton(const_name)
            button.setStyleSheet("background-color: #9b59b6; color: white;")
            button.clicked.connect(lambda checked, c=const_name: self.insert_text(c))
            buttons_layout.addWidget(button, row, col)
        
        # 添加括号和运算符
        operators = [
            ('(', 3, 0), (')', 3, 1), ('+', 3, 2), ('-', 3, 3), ('*', 3, 4),
            ('/', 4, 0), ('^', 4, 1), ('%', 4, 2), (',', 4, 3), ('=', 4, 4)
        ]
        
        for op_text, row, col in operators:
            button = QPushButton(op_text)
            color = "#2ecc71" if op_text == "=" else "#3498db"
            button.setStyleSheet(f"background-color: {color}; color: white;")
            if op_text == "=":
                button.clicked.connect(self.calculate_expression)
            else:
                button.clicked.connect(lambda checked, o=op_text: self.insert_text(o))
            buttons_layout.addWidget(button, row, col)
        
        # 单位转换部分
        units_label = QLabel("单位转换:")
        units_label.setStyleSheet("background-color: transparent; color: #7f8c8d;")
        buttons_layout.addWidget(units_label, 5, 0)
        
        # 添加一些常用单位转换按钮
        unit_conversions = [
            ('m→cm', 5, 1, 'm_to_cm'), 
            ('cm→m', 5, 2, 'cm_to_m'),
            ('kg→lb', 5, 3, 'kg_to_lb'),
            ('C→F', 5, 4, 'c_to_f')
        ]
        
        for btn_text, row, col, unit_code in unit_conversions:
            button = QPushButton(btn_text)
            button.setStyleSheet("background-color: #e67e22; color: white;")
            button.clicked.connect(lambda checked, u=unit_code: self.insert_unit_conversion(u))
            buttons_layout.addWidget(button, row, col)
        
        # 清除和帮助按钮
        clear_button = QPushButton("清除")
        clear_button.setStyleSheet("background-color: #e74c3c; color: white;")
        clear_button.clicked.connect(self.reset_calculator)
        buttons_layout.addWidget(clear_button, 6, 0, 1, 2)
        
        help_button = QPushButton("帮助")
        help_button.setStyleSheet("background-color: #7f8c8d; color: white;")
        help_button.clicked.connect(self.show_expression_help)
        buttons_layout.addWidget(help_button, 6, 2, 1, 3)
        
        layout.addWidget(buttons_frame)
    
    def switch_calculator_mode(self, checked):
        if checked:
            if self.sender() == self.standard_mode:
                self.stacked_widget.setCurrentIndex(0)
                self.setGeometry(300, 300, 380, 500)
                self.display.setReadOnly(True)
            elif self.sender() == self.scientific_mode:
                self.stacked_widget.setCurrentIndex(1)
                self.setGeometry(300, 300, 500, 600)
                self.display.setReadOnly(True)
            elif self.sender() == self.expression_mode:
                self.stacked_widget.setCurrentIndex(2)
                self.setGeometry(300, 300, 500, 650)
                self.display.setReadOnly(False)
                self.display.setCursorPosition(len(self.display.text()))
                self.display.setFocus()
    
    def button_clicked(self):
        sender = self.sender()
        text = sender.text()
        
        if text == 'C':  # 清除
            self.reset_calculator()
        elif text == '⌫':  # 退格
            self.backspace()
        elif text == '±':  # 正负号
            self.negate()
        elif text == '=':  # 等于
            self.calculate_result()
        elif text in ['+', '-', '×', '÷', 'xʸ']:  # 运算符
            self.set_operator(text)
        elif text == '.':  # 小数点
            self.add_decimal_point()
        elif text in ['sin', 'cos', 'tan', 'sqrt', '√', 'ln', 'log', '1/x', 'x²', 'x³']:  # 科学计算器函数
            self.apply_function(text)
        elif text == 'π':  # 圆周率
            self.add_constant(math.pi)
        elif text == 'e':  # 自然对数的底
            self.add_constant(math.e)
        elif text == '(' or text == ')':  # 括号
            self.add_bracket(text)
        else:  # 数字
            self.add_digit(text)
    
    def reset_calculator(self):
        """重置计算器状态"""
        self.display.setText("0")
        self.history_display.setText("")
        self.current_op = ""
        self.first_number = 0
        self.new_number = True
        self.last_button_was_equal = False
        self.brackets_count = 0
    
    def backspace(self):
        """删除最后一个字符"""
        current = self.display.text()
        if len(current) > 1:
            self.display.setText(current[:-1])
        else:
            self.display.setText("0")
            self.new_number = True
    
    def negate(self):
        """改变数字正负号"""
        current = self.display.text()
        if current != "0":
            if current.startswith('-'):
                self.display.setText(current[1:])
            else:
                self.display.setText('-' + current)
    
    def add_decimal_point(self):
        """添加小数点"""
        current = self.display.text()
        if '.' not in current:
            if self.new_number:
                self.display.setText("0.")
                self.new_number = False
            else:
                self.display.setText(current + ".")
    
    def add_digit(self, digit):
        """添加数字"""
        current = self.display.text()
        if self.new_number:
            self.display.setText(digit)
            self.new_number = False
        else:
            if current == "0":
                self.display.setText(digit)
            else:
                self.display.setText(current + digit)
    
    def set_operator(self, operator):
        """设置运算符"""
        try:
            # 如果已经有一个等待的操作，先计算它
            if self.current_op and not self.new_number and not self.last_button_was_equal:
                self.calculate_result()
            
            # 保存当前显示的数字作为第一个操作数
            self.first_number = float(self.display.text())
            
            # 设置新的运算符
            self.current_op = operator
            
            # 更新历史显示
            self.history_display.setText(f"{self.first_number} {self.current_op}")
            
            # 准备输入下一个数字
            self.new_number = True
            self.last_button_was_equal = False
        except Exception as e:
            self.display.setText("错误")
            self.new_number = True
    
    def calculate_result(self):
        """计算结果"""
        try:
            # 获取当前显示的数字作为第二个操作数
            current = self.display.text()
            second_number = float(current)
            
            # 如果没有运算符，直接返回
            if not self.current_op and not self.last_button_was_equal:
                return
            
            # 更新历史显示
            if not self.last_button_was_equal:
                self.history_display.setText(f"{self.first_number} {self.current_op} {second_number} =")
            
            # 根据运算符计算结果
            if self.current_op == '+':
                result = self.first_number + second_number
            elif self.current_op == '-':
                result = self.first_number - second_number
            elif self.current_op == '×':
                result = self.first_number * second_number
            elif self.current_op == '÷':
                if second_number == 0:
                    self.display.setText("除数不能为零")
                    self.new_number = True
                    return
                result = self.first_number / second_number
            elif self.current_op == 'xʸ':
                result = self.first_number ** second_number
            else:
                result = second_number
            
            # 处理整数结果
            if result == int(result):
                result = int(result)
            
            # 显示结果
            self.display.setText(str(result))
            
            # 设置状态
            self.first_number = result
            self.last_button_was_equal = True
            self.new_number = True
        except Exception as e:
            self.display.setText("错误")
            self.new_number = True
    
    def apply_function(self, function):
        """应用数学函数"""
        try:
            # 获取当前显示的数字
            current = self.display.text()
            value = float(current)
            
            # 根据函数类型计算结果
            if function == 'sin':
                result = math.sin(value)
                function_display = f"sin({value})"
            elif function == 'cos':
                result = math.cos(value)
                function_display = f"cos({value})"
            elif function == 'tan':
                result = math.tan(value)
                function_display = f"tan({value})"
            elif function == 'ln':
                if value <= 0:
                    self.display.setText("无效输入")
                    self.new_number = True
                    return
                result = math.log(value)
                function_display = f"ln({value})"
            elif function == 'log':
                if value <= 0:
                    self.display.setText("无效输入")
                    self.new_number = True
                    return
                result = math.log10(value)
                function_display = f"log({value})"
            elif function == '√' or function == 'sqrt':
                if value < 0:
                    self.display.setText("无效输入")
                    self.new_number = True
                    return
                result = math.sqrt(value)
                function_display = f"√({value})"
            elif function == 'x²':
                result = value ** 2
                function_display = f"({value})²"
            elif function == 'x³':
                result = value ** 3
                function_display = f"({value})³"
            elif function == '1/x':
                if value == 0:
                    self.display.setText("除数不能为零")
                    self.new_number = True
                    return
                result = 1 / value
                function_display = f"1/({value})"
            else:
                self.display.setText("未知函数")
                self.new_number = True
                return
            
            # 更新历史显示
            self.history_display.setText(f"{function_display} =")
            
            # 处理整数结果
            if result == int(result):
                result = int(result)
            
            # 显示结果
            self.display.setText(str(result))
            
            # 设置状态
            self.first_number = result
            self.last_button_was_equal = True
            self.new_number = True
        except Exception as e:
            self.display.setText("错误")
            self.new_number = True
    
    def add_constant(self, value):
        """添加常数（如π或e）"""
        # 处理整数常数
        if value == int(value):
            value = int(value)
        
        # 显示常数值
        self.display.setText(str(value))
        self.new_number = True
    
    def add_bracket(self, bracket):
        """添加括号"""
        if bracket == '(':
            if not self.new_number:
                # 如果不是新数字，则添加乘法运算符
                self.set_operator('×')
            self.display.setText('(')
            self.brackets_count += 1
            self.new_number = True
        elif bracket == ')':
            if self.brackets_count > 0:
                # TODO: 在将来实现完整的表达式解析器
                pass
    
    def toggle_theme(self):
        """切换主题"""
        # 切换主题
        self.theme_manager.toggle_theme()
        # 应用新主题
        self.apply_current_theme()
    
    def apply_current_theme(self):
        """应用当前主题样式表"""
        try:
            # 获取当前应用程序实例
            app = QApplication.instance()
            # 应用主题
            self.theme_manager.apply_theme(app)
        except Exception as e:
            print(f"应用主题时出错: {str(e)}")

    def on_display_changed(self, text):
        # 仅在表达式模式下响应文本变化
        if hasattr(self, 'expression_mode') and self.expression_mode.isChecked():
            # 可以在这里添加实时验证或自动完成功能
            pass

    def insert_function(self, function_name):
        """插入函数名和左括号"""
        if self.expression_mode.isChecked():
            if self.display.text() == "0":
                self.display.setText(f"{function_name}(")
            else:
                current_pos = self.display.cursorPosition()
                current_text = self.display.text()
                new_text = current_text[:current_pos] + f"{function_name}(" + current_text[current_pos:]
                self.display.setText(new_text)
                self.display.setCursorPosition(current_pos + len(function_name) + 1)

    def insert_text(self, text):
        """在当前光标位置插入文本"""
        if self.expression_mode.isChecked():
            if self.display.text() == "0" and text not in ['.', '+', '-', '*', '/', '^', '%', ')', ',']:
                self.display.setText(text)
            else:
                current_pos = self.display.cursorPosition()
                current_text = self.display.text()
                new_text = current_text[:current_pos] + text + current_text[current_pos:]
                self.display.setText(new_text)
                self.display.setCursorPosition(current_pos + len(text))

    def insert_unit_conversion(self, unit_code):
        """插入单位转换函数"""
        if self.expression_mode.isChecked():
            self.insert_text(f"convert(,{unit_code})")
            # 将光标定位到参数位置
            current_pos = self.display.cursorPosition()
            self.display.setCursorPosition(current_pos - len(unit_code) - 2)

    def calculate_expression(self):
        """计算表达式的值"""
        if self.expression_mode.isChecked():
            expression = self.display.text()
            self.history_display.setText(f"{expression} =")
            
            try:
                result = self.evaluator.evaluate(expression)
                # 处理整数结果
                if result == int(result):
                    result = int(result)
                self.display.setText(str(result))
            except Exception as e:
                self.display.setText(f"错误: {str(e)}")

    def show_expression_help(self):
        """显示表达式计算器帮助信息"""
        help_text = """
表达式计算器支持以下功能:

1. 数学函数:
   - sin, cos, tan: 三角函数
   - asin, acos, atan: 反三角函数
   - sqrt: 平方根
   - log: 常用对数(底数10)
   - ln: 自然对数
   - exp: e的指数
   - abs: 绝对值
   - round, floor, ceil: 四舍五入、向下取整、向上取整

2. 常量:
   - pi: 圆周率 (3.14159...)
   - e: 自然对数底数 (2.71828...)
   - phi: 黄金比例 (1.61803...)
   - c: 光速 (299792458 m/s)
   - g: 重力加速度 (9.80665 m/s²)

3. 运算符:
   - +, -, *, /: 加减乘除
   - ^: 幂运算
   - %: 取模(余数)

4. 单位转换:
   - 长度: m_to_cm, cm_to_m, m_to_km, km_to_m...
   - 重量: kg_to_g, g_to_kg, kg_to_lb, lb_to_kg...
   - 温度: c_to_f, f_to_c, c_to_k, k_to_c...

使用示例:
- 2 + 2
- sin(pi/4)
- convert(100, m_to_cm)
- sqrt(16) + ln(e^2)
"""
        QMessageBox.information(self, "表达式计算器帮助", help_text)


# 用于独立测试
if __name__ == '__main__':
    app = QApplication(sys.argv)
    calculator = CalculatorWindow()
    calculator.show()
    sys.exit(app.exec()) 