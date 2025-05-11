# src/data/data_manager.py
import os
import json
from typing import List, Dict, Any, Optional, TypeVar, Generic, Callable

T = TypeVar('T')

class DataManager(Generic[T]):
    """通用数据管理器，用于处理JSON数据的加载和保存"""
    
    def __init__(self, file_name: str, data_converter: Optional[Callable[[Dict], T]] = None,
                 data_serializer: Optional[Callable[[T], Dict]] = None):
        """
        初始化数据管理器
        
        Args:
            file_name: 数据文件名（不包含路径）
            data_converter: 将字典转换为对象的函数
            data_serializer: 将对象转换为字典的函数
        """
        self.file_name = file_name
        self.data_converter = data_converter
        self.data_serializer = data_serializer
        self._data_file_path = self._get_data_file_path()
        self._data: List[Dict[str, Any]] = []
        
    def _get_data_file_path(self) -> str:
        """确定数据文件的路径，保存到项目根目录的data文件夹"""
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 获取项目根目录（向上两级）
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            # 确保data目录存在
            data_dir = os.path.join(project_root, "data")
            os.makedirs(data_dir, exist_ok=True)
            return os.path.join(data_dir, self.file_name)
        except Exception as e:
            print(f"Error determining data file path: {e}")
            # 回退到当前目录
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.file_name)
    
    def load_data(self) -> List[Dict[str, Any]]:
        """从JSON文件加载数据"""
        if not os.path.exists(self._data_file_path):
            self._data = []
            return self._data
            
        try:
            with open(self._data_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"Warning: {self.file_name} does not contain a list. Resetting.")
                    self._data = []
                else:
                    # 基本验证（确保是字典列表且每个字典都有id字段）
                    self._data = [item for item in data if isinstance(item, dict) and 'id' in item]
        except (json.JSONDecodeError, IOError, Exception) as e:
            print(f"Error loading data from {self.file_name}: {e}")
            self._data = []
            
        return self._data
    
    def save_data(self, data: Optional[List[Dict[str, Any]]] = None) -> bool:
        """保存数据到JSON文件"""
        if data is not None:
            self._data = data
            
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self._data_file_path), exist_ok=True)
            with open(self._data_file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except (IOError, Exception) as e:
            print(f"Error saving data to {self.file_name}: {e}")
            return False
    
    def get_data(self) -> List[Dict[str, Any]]:
        """获取当前数据"""
        return self._data
    
    def add_item(self, item: Dict[str, Any]) -> bool:
        """添加一个数据项"""
        if not isinstance(item, dict) or 'id' not in item:
            return False
        self._data.append(item)
        return self.save_data()
    
    def update_item(self, item_id: str, updated_item: Dict[str, Any]) -> bool:
        """更新指定ID的数据项"""
        if not isinstance(updated_item, dict) or 'id' not in updated_item:
            return False
            
        for i, item in enumerate(self._data):
            if item.get('id') == item_id:
                self._data[i] = updated_item
                return self.save_data()
                
        # 如果没有找到匹配的ID，添加为新项
        self._data.append(updated_item)
        return self.save_data()
    
    def delete_item(self, item_id: str) -> bool:
        """删除指定ID的数据项"""
        initial_len = len(self._data)
        self._data = [item for item in self._data if item.get('id') != item_id]
        if len(self._data) < initial_len:
            return self.save_data()
        return False
    
    def get_item_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取数据项"""
        for item in self._data:
            if item.get('id') == item_id:
                return item
        return None


class TodoDataManager(DataManager):
    """待办事项数据管理器"""
    
    def __init__(self):
        super().__init__("todo_list.json")
        self.load_data()
    
    def filter_items(self, status_filter: str = "全部", priority_filter: str = "全部") -> List[Dict[str, Any]]:
        """根据状态和优先级过滤待办事项"""
        filtered_data = []
        for item in self._data:
            # 状态过滤
            show = True
            if status_filter == "未完成" and item.get("completed", False):
                show = False
            if status_filter == "已完成" and not item.get("completed", False):
                show = False
            # 优先级过滤
            if priority_filter != "全部" and item.get("priority", "中") != priority_filter:
                show = False
            if show:
                filtered_data.append(item)
        return filtered_data
    
    def sort_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对待办事项进行排序"""
        def sort_key(item):
            prio_val = {"高": 0, "中": 1, "低": 2}.get(item.get("priority", "中"), 1)
            due_date = item.get("due_date", "9999-99-99") or "9999-99-99"
            completed = 1 if item.get("completed", False) else 0
            created = item.get("created_at", "")
            return (completed, due_date, prio_val, created)  # 按完成状态、截止日期、优先级、创建时间排序
        
        return sorted(items, key=sort_key)


class StickyNoteDataManager(DataManager):
    """便签数据管理器"""
    
    def __init__(self):
        super().__init__("sticky_notes.json")
        self.load_data()