# -*- coding: utf-8 -*-
"""
Flask 应用工厂 - 重构版本
"""

import os
import logging
from datetime import timedelta
from flask import Flask

# 设置环境变量以禁用懒加载，避免运行时导入错误
os.environ['YTDLP_NO_LAZY_EXTRACTORS'] = '1'

logger = logging.getLogger(__name__)

def _fix_directory_permissions(directory):
    """强力修复目录权限"""
    try:
        import stat
        import subprocess

        # 尝试多种权限修复方式
        methods = [
            lambda: os.chmod(directory, 0o777),
            lambda: os.chmod(directory, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO),
            lambda: subprocess.run(['chmod', '777', directory], check=False, capture_output=True),
            lambda: subprocess.run(['chown', '-R', f'{os.getuid()}:{os.getgid()}', directory], check=False, capture_output=True),
        ]

        for i, method in enumerate(methods):
            try:
                method()
                logger.debug(f"✅ 权限修复方法 {i+1} 成功")
                break
            except Exception as e:
                logger.debug(f"⚠️ 权限修复方法 {i+1} 失败: {e}")
                continue

    except Exception as e:
        logger.debug(f"⚠️ 权限修复过程出错: {e}")

def _test_directory_write(test_file, directory):
    """测试目录写入权限"""
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        logger.info(f"✅ 目录权限验证成功: {directory}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ 目录权限测试失败: {e}")
        return False

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)

    # 配置应用
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'your-secret-key-change-this'),
        DOWNLOAD_FOLDER=os.environ.get('DOWNLOAD_FOLDER', '/app/downloads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024 * 1024,  # 16GB
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
    )

    # 设置日志
    if not app.debug:
        logging.basicConfig(level=logging.INFO)

    # 在应用上下文中初始化
    with app.app_context():
        _initialize_app(app)

    # 注册蓝图
    _register_blueprints(app)

    return app

def _initialize_app(app):
    """初始化应用组件"""
    try:
        # 初始化目录
        _init_directories(app)

        # 初始化 yt-dlp
        from .core.ytdlp_manager import initialize_ytdlp
        if initialize_ytdlp():
            logger.info("✅ yt-dlp 初始化成功")
        else:
            logger.warning("⚠️ yt-dlp 初始化失败，但应用将继续运行")

        # 初始化文件清理管理器
        _init_cleanup_manager(app)

    except Exception as e:
        logger.error(f"应用初始化失败: {e}")

def _init_directories(app):
    """初始化目录"""
    try:
        download_folder = app.config['DOWNLOAD_FOLDER']
        os.makedirs(download_folder, exist_ok=True)
        logger.info(f"下载目录已创建: {download_folder}")

        # 尝试修复权限
        try:
            os.chmod(download_folder, 0o777)
        except Exception:
            pass  # 忽略权限修改失败

        # 强力权限修复
        _fix_directory_permissions(download_folder)

        # 权限测试
        test_file = os.path.join(download_folder, '.write_test')
        if not _test_directory_write(test_file, download_folder):
            # 如果权限测试失败，尝试使用临时目录
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix='ytdlp_downloads_')
            app.config['DOWNLOAD_FOLDER'] = temp_dir
            logger.info(f"🔄 使用临时目录作为下载目录: {temp_dir}")

            # 确保临时目录权限正确
            _fix_directory_permissions(temp_dir)

            # 再次测试临时目录
            temp_test_file = os.path.join(temp_dir, '.write_test')
            if not _test_directory_write(temp_test_file, temp_dir):
                logger.error("❌ 临时目录也无法写入，可能存在系统级权限问题")

    except Exception as e:
        logger.error(f"目录初始化失败: {e}")
        # 使用系统临时目录作为最后备用
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix='ytdlp_fallback_')
        app.config['DOWNLOAD_FOLDER'] = temp_dir
        logger.info(f"🆘 使用系统临时目录: {temp_dir}")

def _init_cleanup_manager(app):
    """初始化文件清理管理器"""
    try:
        from .file_cleaner import initialize_cleanup_manager

        cleanup_config = {
            'auto_cleanup_enabled': True,
            'cleanup_interval_hours': 1,
            'file_retention_hours': 24,
            'max_storage_mb': 2048,
            'cleanup_on_download': True,
            'keep_recent_files': 20,
            'temp_file_retention_minutes': 30,
        }

        initialize_cleanup_manager(app.config['DOWNLOAD_FOLDER'], cleanup_config)
        logger.info("✅ 文件清理管理器初始化成功")

    except Exception as e:
        logger.error(f"文件清理管理器初始化失败: {e}")

def _register_blueprints(app):
    """注册蓝图"""
    try:
        from .routes import main_bp, auth_bp, api_bp, admin_bp, shortcuts_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
        app.register_blueprint(shortcuts_bp, url_prefix='/api/shortcuts')

        logger.info("✅ 蓝图注册成功")

    except Exception as e:
        logger.error(f"蓝图注册失败: {e}")

# 创建应用实例
app = create_app()
