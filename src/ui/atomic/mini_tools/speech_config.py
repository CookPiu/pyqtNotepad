import os
import json
import pyaudio

class SpeechConfig:
    """语音识别配置管理类"""
    
    def __init__(self):
        # 确定配置文件路径 - 使用项目根目录下的data目录
        # 获取项目根目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 从当前文件位置向上导航到项目根目录
        # src/ui/atomic/mini_tools -> 需要向上4级到达项目根目录
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
        
        self.config_dir = os.path.join(project_root, "data", "speech_recognition")
        self.config_file = os.path.join(self.config_dir, "config.json")
        
        # 默认配置
        self.default_config = {
            "app_id": "",
            "api_key": "",
            "secret_key": "",
            "language": "Mandarin",
            "sample_rate": "16000 Hz",
            "microphone_index": 0
        }
        
        # 确保配置目录存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.default_config.copy()
        else:
            return self.default_config.copy()
    
    def save_config(self, config=None):
        """保存配置文件"""
        if config:
            self.config = config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_api_settings(self):
        """获取API设置"""
        return {
            "app_id": self.config.get("app_id", ""),
            "api_key": self.config.get("api_key", ""),
            "secret_key": self.config.get("secret_key", "")
        }
    
    def save_api_settings(self, app_id, api_key, secret_key):
        """保存API设置"""
        self.config["app_id"] = app_id
        self.config["api_key"] = api_key
        self.config["secret_key"] = secret_key
        return self.save_config()
    
    def get_microphone_devices(self):
        """获取系统麦克风设备列表"""
        devices = []
        p = pyaudio.PyAudio()
        
        try:
            # 获取设备数量
            device_count = p.get_device_count()
            
            # 遍历所有设备
            for i in range(device_count):
                device_info = p.get_device_info_by_index(i)
                # 只添加输入设备（麦克风）
                if device_info.get('maxInputChannels') > 0:
                    name = device_info.get('name')
                    devices.append({
                        'index': i,
                        'name': name
                    })
        finally:
            p.terminate()
        
        return devices
    
    def get_selected_microphone_index(self):
        """获取选中的麦克风索引"""
        return self.config.get("microphone_index", 0)
    
    def save_microphone_selection(self, index):
        """保存麦克风选择"""
        self.config["microphone_index"] = index
        return self.save_config()
    
    def get_language(self):
        """获取语言设置"""
        return self.config.get("language", "Mandarin")
    
    def save_language(self, language):
        """保存语言设置"""
        self.config["language"] = language
        return self.save_config()
    
    def get_sample_rate(self):
        """获取采样率设置"""
        return self.config.get("sample_rate", "16000 Hz")
    
    def save_sample_rate(self, sample_rate):
        """保存采样率设置"""
        self.config["sample_rate"] = sample_rate
        return self.save_config()