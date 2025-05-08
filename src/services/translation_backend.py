# -*- coding: utf-8 -*-
"""
翻译后端服务 - 异步处理翻译请求
"""
import os
import json
import random
import hashlib
import threading
import queue
import time
import requests
from typing import Dict, Tuple, Optional, Callable, List
from PyQt6.QtCore import QObject, pyqtSignal

class TranslationSignalEmitter(QObject):
    """用于发送翻译结果信号的类"""
    translation_completed = pyqtSignal(str, bool, str, object)

# 创建全局信号发射器
_signal_emitter = TranslationSignalEmitter()

class TranslationBackend:
    """翻译后端服务，异步处理翻译请求"""
    
    # 百度翻译API地址
    BAIDU_API_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    
    # API凭据保存路径
    API_CREDENTIALS_DIR = "D:\\pyqtNotepad\\data\\API"
    API_CREDENTIALS_FILE = "baidu_translate_credentials.json"
    
    def __init__(self):
        """初始化翻译后端服务"""
        self.app_id = ""
        self.app_secret = ""
        self.request_queue = queue.Queue()
        self.response_callbacks = {}
        self.worker_thread = None
        self.is_running = False
        self.signal_emitter = _signal_emitter
        
        # 加载API凭据
        self.load_credentials_from_file()
        
        # 启动工作线程
        self.start_worker()
    
    def start_worker(self):
        """启动工作线程"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
    
    def stop_worker(self):
        """停止工作线程"""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            self.request_queue.put(None)  # 发送停止信号
            self.worker_thread.join(timeout=1.0)
    
    def _worker_loop(self):
        """工作线程主循环"""
        while self.is_running:
            try:
                # 从队列获取请求，如果队列为空，最多等待1秒
                request = self.request_queue.get(timeout=1.0)
                
                # 检查是否为停止信号
                if request is None:
                    break
                
                # 解析请求
                request_id, text, from_lang, to_lang, callback = request
                
                # 执行翻译
                success, result, raw_result = self._translate(text, from_lang, to_lang)
                
                # 通过信号发送结果到主线程
                self.signal_emitter.translation_completed.emit(request_id, success, result, raw_result)
                
            except queue.Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                print(f"翻译工作线程错误: {e}")
                # 继续循环，不让工作线程因为单个请求的错误而终止
                continue
    
    def translate_async(self, text: str, from_lang: str = "auto", to_lang: str = "zh", 
                   callback: Callable[[bool, str, Optional[Dict]], None] = None) -> str:
        """
        异步翻译文本
        
        Args:
            text: 要翻译的文本
            from_lang: 源语言代码，默认为自动检测
            to_lang: 目标语言代码，默认为中文
            callback: 翻译完成后的回调函数，接收参数(成功状态, 翻译结果或错误消息, 原始响应数据)
            
        Returns:
            请求ID，可用于取消请求
        """
        try:
            if not self.has_credentials():
                if callback:
                    # 使用信号在主线程中调用回调
                    request_id = str(time.time()) + str(random.randint(1000, 9999))
                    self.response_callbacks[request_id] = callback
                    self.signal_emitter.translation_completed.emit(
                        request_id, False, "未设置百度翻译API凭据", None
                    )
                return ""
                
            if not text:
                if callback:
                    # 使用信号在主线程中调用回调
                    request_id = str(time.time()) + str(random.randint(1000, 9999))
                    self.response_callbacks[request_id] = callback
                    self.signal_emitter.translation_completed.emit(
                        request_id, False, "未提供要翻译的文本", None
                    )
                return ""
            
            # 生成请求ID
            request_id = str(time.time()) + str(random.randint(1000, 9999))
            
            # 存储回调函数
            if callback:
                self.response_callbacks[request_id] = callback
            
            # 将请求加入队列
            self.request_queue.put((request_id, text, from_lang, to_lang, callback))
            
            # 确保工作线程正在运行
            self.start_worker()
            
            return request_id
        except Exception as e:
            error_msg = f"翻译后端异常: {str(e)}"
            print(error_msg)
            if callback:
                # 使用信号在主线程中调用回调
                request_id = str(time.time()) + str(random.randint(1000, 9999))
                self.response_callbacks[request_id] = callback
                self.signal_emitter.translation_completed.emit(
                    request_id, False, error_msg, None
                )
            return ""
    
    def cancel_request(self, request_id: str) -> bool:
        """
        取消翻译请求
        
        Args:
            request_id: 请求ID
            
        Returns:
            是否成功取消
        """
        if request_id in self.response_callbacks:
            del self.response_callbacks[request_id]
            return True
        return False
    
    def _translate(self, text: str, from_lang: str = "auto", to_lang: str = "zh") -> Tuple[bool, str, Optional[Dict]]:
        """
        执行翻译请求（在工作线程中调用）
        
        Args:
            text: 要翻译的文本
            from_lang: 源语言代码，默认为自动检测
            to_lang: 目标语言代码，默认为中文
            
        Returns:
            (成功状态, 翻译结果或错误消息, 原始响应数据)
        """
        try:
            # 构建请求参数
            salt = str(random.randint(32768, 65536))
            sign = self.app_id + text + salt + self.app_secret
            sign = hashlib.md5(sign.encode()).hexdigest()
            
            params = {
                'appid': self.app_id,
                'q': text,
                'from': from_lang,
                'to': to_lang,
                'salt': salt,
                'sign': sign
            }
            
            response = requests.post(self.BAIDU_API_URL, params=params, timeout=10)  # 添加超时参数
            result = response.json()
            
            if 'error_code' in result:
                error_msg = f"百度翻译API错误: {result.get('error_code')} - {result.get('error_msg', '未知错误')}"
                return False, error_msg, result
                
            if 'trans_result' in result and result['trans_result']:
                translated_text = result['trans_result'][0]['dst']
                return True, translated_text, result
            else:
                return False, "未获取到翻译结果", result
                
        except requests.exceptions.Timeout:
            return False, "翻译请求超时，请稍后重试", None
        except requests.exceptions.ConnectionError:
            return False, "网络连接错误，请检查网络设置", None
        except Exception as e:
            return False, f"翻译请求错误: {str(e)}", None
    
    def set_credentials(self, app_id: str, app_secret: str) -> None:
        """
        设置百度翻译API的凭据
        
        Args:
            app_id: 百度翻译API的APP ID
            app_secret: 百度翻译API的密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret
        
    def has_credentials(self) -> bool:
        """检查是否已设置凭据"""
        return bool(self.app_id and self.app_secret)
    
    def get_credentials_file_path(self) -> str:
        """获取凭据文件的完整路径"""
        return os.path.join(self.API_CREDENTIALS_DIR, self.API_CREDENTIALS_FILE)
    
    def save_credentials_to_file(self) -> bool:
        """
        将当前的API凭据保存到文件
        
        Returns:
            bool: 是否成功保存
        """
        if not self.has_credentials():
            return False
            
        try:
            # 确保目录存在
            os.makedirs(self.API_CREDENTIALS_DIR, exist_ok=True)
            
            # 保存凭据到JSON文件
            credentials = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            with open(self.get_credentials_file_path(), 'w', encoding='utf-8') as f:
                json.dump(credentials, f, ensure_ascii=False, indent=2)
                
            return True
        except Exception as e:
            print(f"保存API凭据失败: {e}")
            return False
            
    def load_credentials_from_file(self) -> bool:
        """
        从文件中加载API凭据
        
        Returns:
            bool: 是否成功加载
        """
        try:
            file_path = self.get_credentials_file_path()
            if not os.path.exists(file_path):
                return False
                
            with open(file_path, 'r', encoding='utf-8') as f:
                credentials = json.load(f)
                
            self.app_id = credentials.get("app_id", "")
            self.app_secret = credentials.get("app_secret", "")
            
            return self.has_credentials()
        except Exception as e:
            print(f"加载API凭据失败: {e}")
            return False

# 创建全局后端实例
_translation_backend_instance = None

def get_translation_backend():
    """获取全局翻译后端实例"""
    global _translation_backend_instance
    if _translation_backend_instance is None:
        _translation_backend_instance = TranslationBackend()
        
        # 连接信号到处理函数
        _translation_backend_instance.signal_emitter.translation_completed.connect(
            _handle_translation_completed
        )
        
    return _translation_backend_instance

def _handle_translation_completed(request_id, success, result, raw_result):
    """处理翻译完成信号（在主线程中执行）"""
    backend = get_translation_backend()
    if request_id in backend.response_callbacks:
        try:
            callback = backend.response_callbacks.pop(request_id)
            if callback:
                callback(success, result, raw_result)
        except Exception as e:
            print(f"处理翻译回调时出错: {e}")