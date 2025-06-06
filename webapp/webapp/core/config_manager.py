"""
统一配置管理模块
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self._config = {}
        self._load_default_config()
        self._load_environment_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        
        self._config.update({
            # 路径配置
            'PROJECT_ROOT': str(project_root),
            'DOWNLOAD_FOLDER': '/app/downloads',
            'CONFIG_FOLDER': '/app/config',
            'LOG_FOLDER': '/app/logs',
            'CACHE_FOLDER': '/app/yt-dlp-cache',
            'DATABASE_PATH': '/app/app.db',
            
            # 应用配置
            'SECRET_KEY': 'your-secret-key-change-this',
            'DEBUG': False,
            'HOST': '0.0.0.0',
            'PORT': 8080,
            
            # 数据库配置
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024 * 1024,  # 16GB
            
            # 会话配置
            'SESSION_TIMEOUT_DAYS': 30,
            
            # 下载配置
            'MAX_CONCURRENT_DOWNLOADS': 3,
            'DOWNLOAD_TIMEOUT': 300,
            
            # 文件清理配置
            'AUTO_CLEANUP_ENABLED': True,
            'CLEANUP_INTERVAL_HOURS': 1,
            'FILE_RETENTION_HOURS': 24,
            'MAX_STORAGE_MB': 2048,
            'CLEANUP_ON_DOWNLOAD': True,
            'KEEP_RECENT_FILES': 20,
            'TEMP_FILE_RETENTION_MINUTES': 30,
            
            # Telegram 配置
            'TELEGRAM_ENABLED': False,
            'TELEGRAM_BOT_TOKEN': '',
            'TELEGRAM_CHAT_ID': '',
            'TELEGRAM_API_ID': None,
            'TELEGRAM_API_HASH': '',
            
            # yt-dlp 配置
            'YTDLP_VERSION': 'latest',
            'YTDLP_INSTALL_MODE': 'build-time',  # build-time, runtime, hybrid
            
            # 安全配置
            'ADMIN_USERNAME': 'admin',
            'ADMIN_PASSWORD': 'admin123',
            
            # 日志配置
            'LOG_LEVEL': 'INFO',
            'LOG_FORMAT': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        })
    
    def _load_environment_config(self):
        """从环境变量加载配置"""
        env_mappings = {
            'SECRET_KEY': 'SECRET_KEY',
            'DOWNLOAD_FOLDER': 'DOWNLOAD_FOLDER',
            'CONFIG_FOLDER': 'CONFIG_FOLDER',
            'LOG_FOLDER': 'LOG_FOLDER',
            'CACHE_FOLDER': 'CACHE_FOLDER',
            'DATABASE_PATH': 'DATABASE_PATH',
            'DEBUG': ('DEBUG', bool),
            'HOST': 'HOST',
            'PORT': ('PORT', int),
            'SESSION_TIMEOUT_DAYS': ('SESSION_TIMEOUT_DAYS', int),
            'MAX_CONCURRENT_DOWNLOADS': ('MAX_CONCURRENT_DOWNLOADS', int),
            'DOWNLOAD_TIMEOUT': ('DOWNLOAD_TIMEOUT', int),
            'AUTO_CLEANUP_ENABLED': ('AUTO_CLEANUP_ENABLED', bool),
            'CLEANUP_INTERVAL_HOURS': ('CLEANUP_INTERVAL_HOURS', int),
            'FILE_RETENTION_HOURS': ('FILE_RETENTION_HOURS', int),
            'MAX_STORAGE_MB': ('MAX_STORAGE_MB', int),
            'CLEANUP_ON_DOWNLOAD': ('CLEANUP_ON_DOWNLOAD', bool),
            'KEEP_RECENT_FILES': ('KEEP_RECENT_FILES', int),
            'TEMP_FILE_RETENTION_MINUTES': ('TEMP_FILE_RETENTION_MINUTES', int),
            'TELEGRAM_ENABLED': ('TELEGRAM_ENABLED', bool),
            'TELEGRAM_BOT_TOKEN': 'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID': 'TELEGRAM_CHAT_ID',
            'TELEGRAM_API_ID': ('TELEGRAM_API_ID', int),
            'TELEGRAM_API_HASH': 'TELEGRAM_API_HASH',
            'YTDLP_VERSION': 'YTDLP_VERSION',
            'YTDLP_INSTALL_MODE': 'YTDLP_INSTALL_MODE',
            'ADMIN_USERNAME': 'ADMIN_USERNAME',
            'ADMIN_PASSWORD': 'ADMIN_PASSWORD',
            'LOG_LEVEL': 'LOG_LEVEL',
        }
        
        for config_key, env_config in env_mappings.items():
            if isinstance(env_config, tuple):
                env_key, value_type = env_config
            else:
                env_key = env_config
                value_type = str
            
            env_value = os.environ.get(env_key)
            if env_value is not None:
                try:
                    if value_type == bool:
                        self._config[config_key] = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif value_type == int:
                        self._config[config_key] = int(env_value)
                    else:
                        self._config[config_key] = env_value
                except (ValueError, TypeError):
                    # 如果转换失败，保持默认值
                    pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        self._config[key] = value
    
    def update(self, config_dict: Dict[str, Any]):
        """批量更新配置"""
        self._config.update(config_dict)
    
    def get_flask_config(self) -> Dict[str, Any]:
        """获取 Flask 应用配置"""
        return {
            'SECRET_KEY': self.get('SECRET_KEY'),
            'SQLALCHEMY_DATABASE_URI': f"sqlite:///{self.get('DATABASE_PATH')}",
            'SQLALCHEMY_TRACK_MODIFICATIONS': self.get('SQLALCHEMY_TRACK_MODIFICATIONS'),
            'DOWNLOAD_FOLDER': self.get('DOWNLOAD_FOLDER'),
            'MAX_CONTENT_LENGTH': self.get('MAX_CONTENT_LENGTH'),
            'DEBUG': self.get('DEBUG'),
        }
    
    def get_download_config(self) -> Dict[str, Any]:
        """获取下载配置"""
        return {
            'download_folder': self.get('DOWNLOAD_FOLDER'),
            'max_concurrent': self.get('MAX_CONCURRENT_DOWNLOADS'),
            'timeout': self.get('DOWNLOAD_TIMEOUT'),
        }
    
    def get_cleanup_config(self) -> Dict[str, Any]:
        """获取文件清理配置"""
        return {
            'auto_cleanup_enabled': self.get('AUTO_CLEANUP_ENABLED'),
            'cleanup_interval_hours': self.get('CLEANUP_INTERVAL_HOURS'),
            'file_retention_hours': self.get('FILE_RETENTION_HOURS'),
            'max_storage_mb': self.get('MAX_STORAGE_MB'),
            'cleanup_on_download': self.get('CLEANUP_ON_DOWNLOAD'),
            'keep_recent_files': self.get('KEEP_RECENT_FILES'),
            'temp_file_retention_minutes': self.get('TEMP_FILE_RETENTION_MINUTES'),
        }
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """获取 Telegram 配置"""
        return {
            'enabled': self.get('TELEGRAM_ENABLED'),
            'bot_token': self.get('TELEGRAM_BOT_TOKEN'),
            'chat_id': self.get('TELEGRAM_CHAT_ID'),
            'api_id': self.get('TELEGRAM_API_ID'),
            'api_hash': self.get('TELEGRAM_API_HASH'),
        }
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.get('DOWNLOAD_FOLDER'),
            self.get('CONFIG_FOLDER'),
            self.get('LOG_FOLDER'),
            self.get('CACHE_FOLDER'),
        ]
        
        for directory in directories:
            if directory:
                os.makedirs(directory, exist_ok=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """返回所有配置的字典"""
        return self._config.copy()

# 全局配置实例
config = ConfigManager()

# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """获取配置值的便捷函数"""
    return config.get(key, default)

def set_config(key: str, value: Any):
    """设置配置值的便捷函数"""
    config.set(key, value)

def get_flask_config() -> Dict[str, Any]:
    """获取 Flask 配置的便捷函数"""
    return config.get_flask_config()

def get_download_config() -> Dict[str, Any]:
    """获取下载配置的便捷函数"""
    return config.get_download_config()

def get_cleanup_config() -> Dict[str, Any]:
    """获取清理配置的便捷函数"""
    return config.get_cleanup_config()

def get_telegram_config() -> Dict[str, Any]:
    """获取 Telegram 配置的便捷函数"""
    return config.get_telegram_config()
