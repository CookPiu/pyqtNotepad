# src/data/ics_importer.py
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

class ICSImporter:
    """ICS文件导入器，用于解析.ics文件并提取事件信息"""
    
    def __init__(self):
        """初始化ICS导入器"""
        pass
        
    def _unescape_ics(self, text: str) -> str:
        """处理ICS文件中的转义字符
        
        Args:
            text: 需要处理的文本
            
        Returns:
            str: 处理后的文本
        """
        if not text:
            return ""
            
        # 处理常见的ICS转义序列
        replacements = {
            "\\n": "\n",  # 换行符
            "\\,": ",",   # 逗号
            "\\;": ";",   # 分号
            "\\\\": "\\", # 反斜杠
            "\\N": "\n"   # 另一种换行表示
        }
        
        for escaped, unescaped in replacements.items():
            text = text.replace(escaped, unescaped)
            
        return text
    
    def parse_ics_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """解析ICS文件，提取事件信息
        
        Args:
            file_path: ICS文件路径
            
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: 日历事件列表和待办事项列表
        """
        if not os.path.exists(file_path) or not file_path.lower().endswith('.ics'):
            print(f"错误：文件不存在或不是有效的ICS文件: {file_path}")
            return [], []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试使用其他编码
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                print(f"读取ICS文件时出错: {e}")
                return [], []
        except Exception as e:
            print(f"读取ICS文件时出错: {e}")
            return [], []
        
        # 解析事件
        calendar_events = []
        todo_items = []
        
        # 分割事件块
        event_blocks = re.split(r'BEGIN:(VEVENT|VTODO)', content)
        
        i = 1
        while i < len(event_blocks):
            event_type = event_blocks[i]
            event_content = event_blocks[i+1].split('END:' + event_type)[0] if i+1 < len(event_blocks) else ""
            
            if event_type == 'VEVENT':
                event = self._parse_event(event_content)
                if event:
                    calendar_events.append(event)
                    # 同时创建一个待办事项（如果有截止日期）
                    if 'date' in event:
                        todo = self._event_to_todo(event)
                        if todo:
                            todo_items.append(todo)
            elif event_type == 'VTODO':
                todo = self._parse_todo(event_content)
                if todo:
                    todo_items.append(todo)
            
            i += 2
        
        return calendar_events, todo_items
    
    def _parse_event(self, event_content: str) -> Optional[Dict[str, Any]]:
        """解析VEVENT块，提取事件信息
        
        Args:
            event_content: VEVENT块内容
            
        Returns:
            Dict[str, Any]: 事件信息字典
        """
        event = {}
        
        # 提取基本信息
        summary_match = re.search(r'SUMMARY:(.+?)(?:\r\n|\n|$)', event_content)
        if summary_match:
            event['title'] = self._unescape_ics(summary_match.group(1).strip())
        else:
            event['title'] = "未命名事件"
        
        # 提取描述
        description_match = re.search(r'DESCRIPTION:(.+?)(?:\r\n|\n|$)', event_content)
        if description_match:
            event['description'] = self._unescape_ics(description_match.group(1).strip())
        else:
            event['description'] = ""
        
        # 提取日期和时间
        dtstart_match = re.search(r'DTSTART(?:;.+?)?:(.+?)(?:\r\n|\n|$)', event_content)
        if dtstart_match:
            dt_str = dtstart_match.group(1).strip()
            date_str, time_str = self._parse_datetime(dt_str)
            if date_str:
                event['date'] = date_str
                if time_str:
                    event['time'] = time_str
        
        # 如果没有日期，则跳过此事件
        if 'date' not in event:
            return None
        
        # 生成唯一ID
        event['id'] = str(uuid.uuid4())
        
        # 设置事件类型（默认为"其他"）
        event['type'] = "其他"
        
        return event
    
    def _parse_todo(self, todo_content: str) -> Optional[Dict[str, Any]]:
        """解析VTODO块，提取待办事项信息
        
        Args:
            todo_content: VTODO块内容
            
        Returns:
            Dict[str, Any]: 待办事项信息字典
        """
        todo = {}
        
        # 提取基本信息
        summary_match = re.search(r'SUMMARY:(.+?)(?:\r\n|\n|$)', todo_content)
        if summary_match:
            todo['title'] = self._unescape_ics(summary_match.group(1).strip())
        else:
            todo['title'] = "未命名待办事项"
        
        # 提取描述
        description_match = re.search(r'DESCRIPTION:(.+?)(?:\r\n|\n|$)', todo_content)
        if description_match:
            todo['description'] = self._unescape_ics(description_match.group(1).strip())
        else:
            todo['description'] = ""
        
        # 提取截止日期
        due_match = re.search(r'DUE(?:;.+?)?:(.+?)(?:\r\n|\n|$)', todo_content)
        if due_match:
            dt_str = due_match.group(1).strip()
            date_str, _ = self._parse_datetime(dt_str)
            if date_str:
                todo['due_date'] = date_str
        
        # 如果没有截止日期，则使用当前日期
        if 'due_date' not in todo:
            todo['due_date'] = datetime.now().strftime("%Y-%m-%d")
        
        # 提取优先级
        priority_match = re.search(r'PRIORITY:(.+?)(?:\r\n|\n|$)', todo_content)
        if priority_match:
            priority_value = priority_match.group(1).strip()
            try:
                priority_num = int(priority_value)
                if priority_num <= 3:
                    todo['priority'] = "高"
                elif priority_num <= 6:
                    todo['priority'] = "中"
                else:
                    todo['priority'] = "低"
            except ValueError:
                todo['priority'] = "中"
        else:
            todo['priority'] = "中"
        
        # 提取完成状态
        status_match = re.search(r'STATUS:(.+?)(?:\r\n|\n|$)', todo_content)
        if status_match:
            status = status_match.group(1).strip().upper()
            todo['completed'] = status == "COMPLETED"
        else:
            todo['completed'] = False
        
        # 生成唯一ID
        todo['id'] = str(uuid.uuid4())
        
        return todo
    
    def _event_to_todo(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """将日历事件转换为待办事项
        
        Args:
            event: 日历事件字典
            
        Returns:
            Dict[str, Any]: 待办事项字典
        """
        if not event or 'date' not in event:
            return None
        
        todo = {
            'title': event.get('title', "未命名待办事项"),
            'description': event.get('description', ""),
            'due_date': event.get('date'),
            'priority': "中",
            'completed': False,
            'id': str(uuid.uuid4())
        }
        
        return todo
    
    def _parse_datetime(self, dt_str: str) -> Tuple[Optional[str], Optional[str]]:
        """解析ICS日期时间字符串
        
        Args:
            dt_str: ICS日期时间字符串，格式如：20230101T120000Z
            
        Returns:
            Tuple[Optional[str], Optional[str]]: 日期字符串和时间字符串的元组
        """
        if not dt_str:
            return None, None
        
        # 处理带时区的日期时间
        is_utc = dt_str.endswith('Z')
        if is_utc:
            dt_str = dt_str[:-1]  # 移除Z
        
        # 分离日期和时间
        parts = dt_str.split('T')
        date_part = parts[0] if parts else ""
        time_part = parts[1] if len(parts) > 1 else ""
        
        # 解析日期
        date_str = None
        if len(date_part) >= 8:
            try:
                year = date_part[:4]
                month = date_part[4:6]
                day = date_part[6:8]
                date_str = f"{year}-{month}-{day}"
            except Exception:
                pass
        
        # 解析时间
        time_str = None
        if len(time_part) >= 6:
            try:
                hour = time_part[:2]
                minute = time_part[2:4]
                time_str = f"{hour}:{minute}"
            except Exception:
                pass
        
        return date_str, time_str