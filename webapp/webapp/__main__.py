"""
yt-dlp Web 界面模块入口点
支持 python -m webapp 启动方式
"""

import sys
import os

# 确保正确的导入路径
try:
    from .server import main
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from webapp.server import main

if __name__ == '__main__':
    main()
