#!/usr/bin/env python3
"""
yt-dlp Web 服务器

此模块为 yt-dlp 提供网页界面，允许用户：
- 通过网页浏览器下载视频
- 使用 REST API 端点
- 与 iOS 快捷指令集成
- 监控下载进度

使用方法：
    python -m yt_dlp.web_server [选项]

    或者

    yt-dlp --web-server [选项]
"""

import argparse
import os
import sys
from .web.server import WebServer


def main():
    """Web 服务器的主入口点"""
    parser = argparse.ArgumentParser(
        description='yt-dlp 网页界面',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s                                    # 在 localhost:8080 启动服务器
  %(prog)s --host 0.0.0.0 --port 5000        # 在所有接口的 5000 端口启动服务器
  %(prog)s --download-folder ~/Downloads     # 使用自定义下载文件夹
  %(prog)s --debug                           # 启用调试模式
  %(prog)s --no-browser                      # 不自动打开浏览器

iOS 快捷指令集成：
  使用端点：http://your-server:port/api/shortcuts/download
  发送 POST 请求，包含 'url' 参数和可选的 'audio_only=true'

API 端点：
  POST /api/info                             # 获取视频信息
  POST /api/download                         # 开始下载
  GET  /api/download/<id>/status             # 检查下载状态
  GET  /api/downloads                        # 列出所有下载
  POST /api/shortcuts/download               # iOS 快捷指令端点
        """
    )

    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='绑定的主机地址 (默认: 127.0.0.1)。使用 0.0.0.0 绑定到所有接口'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='绑定的端口 (默认: 8080)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='启用调试模式 (代码更改时自动重载)'
    )

    parser.add_argument(
        '--download-folder',
        default='./downloads',
        help='保存下载文件的文件夹 (默认: ./downloads)'
    )

    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='不自动打开浏览器'
    )

    parser.add_argument(
        '--background',
        action='store_true',
        help='在后台运行服务器 (守护进程模式)'
    )

    args = parser.parse_args()

    # 验证参数
    if args.port < 1 or args.port > 65535:
        print("错误：端口必须在 1 到 65535 之间", file=sys.stderr)
        sys.exit(1)

    # 如果下载文件夹不存在则创建
    download_folder = os.path.abspath(args.download_folder)
    try:
        os.makedirs(download_folder, exist_ok=True)
    except PermissionError:
        print(f"错误：无法创建下载文件夹 '{download_folder}' - 权限被拒绝", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误：无法创建下载文件夹 '{download_folder}' - {e}", file=sys.stderr)
        sys.exit(1)

    # 创建并配置服务器
    server = WebServer(
        host=args.host,
        port=args.port,
        debug=args.debug,
        download_folder=download_folder
    )

    try:
        if args.background:
            # 在后台模式启动
            thread = server.start_background()
            print(f"服务器已在后台启动。线程：{thread}")
            print("按 Ctrl+C 停止服务器")

            # 保持主线程活跃
            try:
                thread.join()
            except KeyboardInterrupt:
                print("\n正在关闭后台服务器...")
        else:
            # 在前台模式启动
            server.start(open_browser=not args.no_browser)

    except KeyboardInterrupt:
        print("\n服务器已被用户停止")
    except Exception as e:
        print(f"启动服务器时出错：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
