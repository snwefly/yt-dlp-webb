"""
服务注册中心 - 解耦组件依赖关系
"""

import logging
from typing import Dict, Any, Optional, Type, TypeVar
from threading import Lock

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ServiceRegistry:
    """服务注册中心，用于管理应用组件的依赖关系"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._lock = Lock()
    
    def register_service(self, name: str, service: Any):
        """注册服务实例"""
        with self._lock:
            self._services[name] = service
            logger.debug(f"注册服务: {name}")
    
    def register_factory(self, name: str, factory: callable):
        """注册服务工厂函数"""
        with self._lock:
            self._factories[name] = factory
            logger.debug(f"注册工厂: {name}")
    
    def register_singleton(self, name: str, factory: callable):
        """注册单例服务"""
        with self._lock:
            self._factories[name] = factory
            logger.debug(f"注册单例: {name}")
    
    def get_service(self, name: str, default: Any = None) -> Any:
        """获取服务实例"""
        # 首先检查已注册的服务
        if name in self._services:
            return self._services[name]
        
        # 检查单例缓存
        if name in self._singletons:
            return self._singletons[name]
        
        # 使用工厂创建
        if name in self._factories:
            with self._lock:
                # 双重检查锁定模式
                if name in self._singletons:
                    return self._singletons[name]
                
                service = self._factories[name]()
                self._singletons[name] = service
                return service
        
        return default
    
    def has_service(self, name: str) -> bool:
        """检查服务是否存在"""
        return (name in self._services or 
                name in self._factories or 
                name in self._singletons)
    
    def clear(self):
        """清空所有服务"""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()

# 全局服务注册中心
_registry = ServiceRegistry()

def get_registry() -> ServiceRegistry:
    """获取全局服务注册中心"""
    return _registry

def register_service(name: str, service: Any):
    """注册服务的便捷函数"""
    _registry.register_service(name, service)

def register_factory(name: str, factory: callable):
    """注册工厂的便捷函数"""
    _registry.register_factory(name, factory)

def register_singleton(name: str, factory: callable):
    """注册单例的便捷函数"""
    _registry.register_singleton(name, factory)

def get_service(name: str, default: Any = None) -> Any:
    """获取服务的便捷函数"""
    return _registry.get_service(name, default)

def inject_service(service_name: str):
    """服务注入装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            service = get_service(service_name)
            if service is None:
                raise ValueError(f"服务 '{service_name}' 未注册")
            return func(service, *args, **kwargs)
        return wrapper
    return decorator

# 服务名称常量
class ServiceNames:
    """服务名称常量"""
    DOWNLOAD_MANAGER = 'download_manager'
    TELEGRAM_NOTIFIER = 'telegram_notifier'
    FILE_CLEANER = 'file_cleaner'
    YTDLP_MANAGER = 'ytdlp_manager'
    CONFIG_MANAGER = 'config_manager'
    ERROR_HANDLER = 'error_handler'
    AUTH_MANAGER = 'auth_manager'

def initialize_core_services(app):
    """初始化核心服务"""
    try:
        # 注册配置管理器
        from .config_manager import config
        register_service(ServiceNames.CONFIG_MANAGER, config)
        
        # 注册下载管理器工厂
        def create_download_manager():
            from .download_manager import DownloadManager
            return DownloadManager(app)
        register_singleton(ServiceNames.DOWNLOAD_MANAGER, create_download_manager)
        
        # 注册 Telegram 通知器工厂
        def create_telegram_notifier():
            from .telegram_notifier import TelegramNotifier
            return TelegramNotifier()
        register_singleton(ServiceNames.TELEGRAM_NOTIFIER, create_telegram_notifier)
        
        # 注册文件清理器工厂
        def create_file_cleaner():
            from ..file_cleaner import FileCleaner
            config_mgr = get_service(ServiceNames.CONFIG_MANAGER)
            return FileCleaner(
                download_folder=config_mgr.get('DOWNLOAD_FOLDER'),
                config=config_mgr.get_cleanup_config()
            )
        register_singleton(ServiceNames.FILE_CLEANER, create_file_cleaner)
        
        # 注册 yt-dlp 管理器工厂
        def create_ytdlp_manager():
            from .ytdlp_manager import YtdlpManager
            return YtdlpManager()
        register_singleton(ServiceNames.YTDLP_MANAGER, create_ytdlp_manager)
        
        logger.info("✅ 核心服务注册完成")
        
    except Exception as e:
        logger.error(f"核心服务初始化失败: {e}")
        raise

def get_download_manager():
    """获取下载管理器的便捷函数"""
    return get_service(ServiceNames.DOWNLOAD_MANAGER)

def get_telegram_notifier():
    """获取 Telegram 通知器的便捷函数"""
    return get_service(ServiceNames.TELEGRAM_NOTIFIER)

def get_file_cleaner():
    """获取文件清理器的便捷函数"""
    return get_service(ServiceNames.FILE_CLEANER)

def get_ytdlp_manager():
    """获取 yt-dlp 管理器的便捷函数"""
    return get_service(ServiceNames.YTDLP_MANAGER)
