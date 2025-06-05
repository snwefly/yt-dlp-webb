"""
yt-dlp 网页界面模块

此模块为 yt-dlp 提供基于网页的界面，包括：
- 用于程序化访问的 REST API
- 用于浏览器交互的网页界面
- iOS 快捷指令集成端点
"""

# 尝试导入，如果失败则提供错误信息
try:
    from .app import create_app
    from .server import WebServer
except ImportError as e:
    import sys
    print(f"❌ webapp 模块导入失败: {e}")
    print("🔧 尝试安装缺失的依赖...")

    # 尝试安装缺失的依赖
    import subprocess
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--no-cache-dir', 'Flask-Login>=0.6.3'])
        print("✅ Flask-Login 安装成功，重新导入...")
        from .app import create_app
        from .server import WebServer
    except Exception as install_error:
        print(f"❌ 依赖安装失败: {install_error}")
        raise e

__all__ = ['create_app', 'WebServer']
