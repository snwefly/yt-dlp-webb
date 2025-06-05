"""
yt-dlp 网页界面的 Web 服务器
"""

import argparse
import os
import sys
import threading
import webbrowser
from .app import create_app


class WebServer:
    """yt-dlp 的 Web 服务器包装器"""

    def __init__(self, host='127.0.0.1', port=8080, debug=True, download_folder=None):
        self.host = host
        self.port = port
        self.debug = debug
        self.download_folder = download_folder or './downloads'
        self.app = None
        self.server_thread = None

    def create_app(self):
        """创建带配置的 Flask 应用程序"""
        # 设置环境变量来配置应用
        import os
        os.environ['DOWNLOAD_FOLDER'] = self.download_folder

        self.app = create_app()

        # 更新应用配置
        self.app.config.update({
            'DOWNLOAD_FOLDER': self.download_folder,
            'DEBUG': self.debug,
        })

        return self.app

    def start(self, open_browser=True):
        """启动 Web 服务器"""
        if not self.app:
            self.create_app()

        print(f"正在启动 yt-dlp Web 服务器：http://{self.host}:{self.port}")
        print(f"下载文件夹：{os.path.abspath(self.download_folder)}")

        if open_browser and not self.debug:
            # 短暂延迟后打开浏览器
            def open_browser_delayed():
                import time
                time.sleep(1)
                webbrowser.open(f'http://{self.host}:{self.port}')

            browser_thread = threading.Thread(target=open_browser_delayed)
            browser_thread.daemon = True
            browser_thread.start()

        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.debug,
                threaded=True
            )
        except KeyboardInterrupt:
            print("\n正在关闭 Web 服务器...")
        except Exception as e:
            print(f"启动 Web 服务器时出错：{e}")
            sys.exit(1)

    def start_background(self):
        """在后台线程中启动 Web 服务器"""
        if not self.app:
            self.create_app()

        def run_server():
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                threaded=True,
                use_reloader=False
            )

        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()

        print(f"yt-dlp Web 服务器已在后台启动：http://{self.host}:{self.port}")
        return self.server_thread


def main():
    """Web 服务器的主入口点"""
    parser = argparse.ArgumentParser(description='yt-dlp 网页界面')
    parser.add_argument('--host', default='127.0.0.1',
                       help='绑定的主机地址 (默认: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8080,
                       help='绑定的端口 (默认: 8080)')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试模式')
    parser.add_argument('--download-folder', default='./downloads',
                       help='保存下载文件的文件夹 (默认: ./downloads)')
    parser.add_argument('--no-browser', action='store_true',
                       help='不自动打开浏览器')

    args = parser.parse_args()

    # 创建并启动服务器
    server = WebServer(
        host=args.host,
        port=args.port,
        debug=args.debug,
        download_folder=args.download_folder
    )

    server.start(open_browser=not args.no_browser)


if __name__ == '__main__':
    main()
