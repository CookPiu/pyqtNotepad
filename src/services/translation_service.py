import hashlib
import random
import requests
import json
import os
from typing import Dict, Optional, Tuple


class TranslationService:
    """百度翻译API服务"""
    
    # 百度翻译API地址
    BAIDU_API_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    
    # API凭据保存路径
    API_CREDENTIALS_DIR = "D:\\pyqtNotepad\\data\\API"
    API_CREDENTIALS_FILE = "baidu_translate_credentials.json"
    
    # 支持的语言代码
    SUPPORTED_LANGUAGES = {
        "自动检测": "auto",
        "中文": "zh",
        "英语": "en",
        "日语": "jp",
        "韩语": "kor",
        "法语": "fra",
        "德语": "de",
        "俄语": "ru",
        "西班牙语": "spa",
        "葡萄牙语": "pt",
        "意大利语": "it",
        "越南语": "vie",
        "泰语": "th",
        "阿拉伯语": "ara",
        "荷兰语": "nl",
        "希腊语": "el",
    }
    
    def __init__(self, app_id: str = "", app_secret: str = ""):
        """
        初始化翻译服务
        
        Args:
            app_id: 百度翻译API的APP ID
            app_secret: 百度翻译API的密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret
        
        # 创建API凭据目录（如果不存在）
        os.makedirs(self.API_CREDENTIALS_DIR, exist_ok=True)
        
        # 如果没有提供凭据，尝试从文件加载
        if not (app_id and app_secret):
            self.load_credentials_from_file()
        
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
    
    def get_language_list(self) -> Dict[str, str]:
        """获取支持的语言列表"""
        return self.SUPPORTED_LANGUAGES
        
    def translate(self, text: str, from_lang: str = "auto", to_lang: str = "zh") -> Tuple[bool, str, Optional[Dict]]:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            from_lang: 源语言代码，默认为自动检测
            to_lang: 目标语言代码，默认为中文
            
        Returns:
            (成功状态, 翻译结果或错误消息, 原始响应数据)
        """
        if not self.has_credentials():
            return False, "未设置百度翻译API凭据", None
            
        if not text:
            return False, "未提供要翻译的文本", None
            
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
        
        try:
            response = requests.post(self.BAIDU_API_URL, params=params)
            result = response.json()
            
            if 'error_code' in result:
                error_msg = f"百度翻译API错误: {result.get('error_code')} - {result.get('error_msg', '未知错误')}"
                return False, error_msg, result
                
            if 'trans_result' in result and result['trans_result']:
                translated_text = result['trans_result'][0]['dst']
                return True, translated_text, result
            else:
                return False, "未获取到翻译结果", result
                
        except Exception as e:
            return False, f"翻译请求错误: {str(e)}", None
            
    def get_error_message(self, error_code: str) -> str:
        """根据错误代码返回友好的错误消息"""
        error_messages = {
            "52000": "成功",
            "52001": "请求超时，请重试",
            "52002": "系统错误，请重试",
            "52003": "未授权用户，请检查您的appid是否正确",
            "54000": "必填参数为空，请检查是否少传参数",
            "54001": "签名错误，请检查您的签名生成方法",
            "54003": "访问频率受限，请降低您的调用频率",
            "54004": "账户余额不足，请前往百度翻译开放平台充值",
            "54005": "长query请求频繁，请降低长query的发送频率",
            "58000": "客户端IP非法，请检查您的IP是否在百度翻译开放平台申请时填写的IP列表内",
            "58001": "译文语言方向不支持，请检查译文语言是否在支持的语言列表内",
            "58002": "服务当前已关闭，请前往百度翻译开放平台开启服务",
        }
        
        return error_messages.get(error_code, f"未知错误 (代码: {error_code})") 