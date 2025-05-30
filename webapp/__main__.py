"""
yt-dlp Web 界面模块入口点
支持 python -m web.server 启动方式
"""

from .server import main

if __name__ == '__main__':
    main()
