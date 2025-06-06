"""
yt-dlp 网页界面模块

此模块为 yt-dlp 提供基于网页的界面，包括：
- 用于程序化访问的 REST API
- 用于浏览器交互的网页界面
- iOS 快捷指令集成端点
"""

# 延迟导入，避免在包导入时触发依赖检查
def create_app(*args, **kwargs):
    """延迟导入的应用工厂函数"""
    from .app import create_app as _create_app
    return _create_app(*args, **kwargs)

def get_web_server():
    """延迟导入的 WebServer 类"""
    from .server import WebServer
    return WebServer

__all__ = ['create_app', 'get_web_server']
