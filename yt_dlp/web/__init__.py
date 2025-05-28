"""
yt-dlp 网页界面模块

此模块为 yt-dlp 提供基于网页的界面，包括：
- 用于程序化访问的 REST API
- 用于浏览器交互的网页界面
- iOS 快捷指令集成端点
"""

from .app import create_app
from .server import WebServer

__all__ = ['create_app', 'WebServer']
