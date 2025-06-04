# -*- coding: utf-8 -*-
"""
Flask 应用工厂 - 重构版本
"""

import os
import logging
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager

# 暂时禁用懒加载以避免 extractor 导入问题
# os.environ['YTDLP_NO_LAZY_EXTRACTORS'] = '1'
os.environ['YTDLP_IGNORE_EXTRACTOR_ERRORS'] = '1'

logger = logging.getLogger(__name__)

def _fix_directory_permissions(directory):
    """修复目录权限（以 root 用户运行，简化处理）"""
    try:
        # 以 root 用户运行，直接设置权限
        os.chmod(directory, 0o755)
        logger.debug(f"✅ 目录权限设置成功: {directory}")
    except Exception as e:
        logger.debug(f"⚠️ 权限设置失败: {e}")

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

    # 配置日志 - 确保输出到容器日志
    if not app.debug:
        import logging
        from logging.config import dictConfig

        dictConfig({
            'version': 1,
            'formatters': {
                'default': {
                    'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
                }
            },
            'handlers': {
                'wsgi': {
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://flask.logging.wsgi_errors_stream',
                    'formatter': 'default'
                }
            },
            'root': {
                'level': 'INFO',
                'handlers': ['wsgi']
            }
        })

        app.logger.info('🚀 Flask 应用已启动，日志系统已配置')

    # 配置应用
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'your-secret-key-change-this'),
        DOWNLOAD_FOLDER=os.environ.get('DOWNLOAD_FOLDER', '/app/downloads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024 * 1024,  # 16GB
        # 增加session超时时间到30天，与AuthManager保持一致
        PERMANENT_SESSION_LIFETIME=timedelta(days=int(os.environ.get('SESSION_TIMEOUT_DAYS', '30')))
    )

    # 设置日志
    if not app.debug:
        logging.basicConfig(level=logging.INFO)

    # 在应用上下文中初始化所有组件
    with app.app_context():
        # 初始化数据库
        _init_database(app)

        # 初始化Flask-Login
        _init_login_manager(app)

        # 初始化其他组件
        _initialize_app(app)

    # 注册蓝图
    _register_blueprints(app)

    return app

def _init_database(app):
    """初始化数据库"""
    try:
        from .models import db

        # 配置数据库 - 使用绝对路径
        db_path = os.path.join(os.getcwd(), 'app.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        logger.info(f"数据库路径: {db_path}")

        # 初始化数据库
        db.init_app(app)

        # 创建表（已经在应用上下文中）
        db.create_all()

        # 创建默认管理员用户
        from .models import User, TelegramConfig
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            logger.info("✅ 默认管理员用户已创建: admin/admin123")
        else:
            logger.info("✅ 管理员用户已存在")

        # 确保Telegram配置存在
        telegram_config = TelegramConfig.query.first()
        if not telegram_config:
            telegram_config = TelegramConfig()
            db.session.add(telegram_config)
            db.session.commit()
            logger.info("✅ 默认Telegram配置已创建")
        else:
            logger.info("✅ Telegram配置已存在")

        logger.info("✅ 数据库初始化成功")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

def _init_login_manager(app):
    """初始化Flask-Login"""
    try:
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        login_manager.login_message = '请先登录以访问此页面。'
        login_manager.login_message_category = 'info'

        @login_manager.user_loader
        def load_user(user_id):
            from .models import User
            return User.query.get(int(user_id))

        logger.info("✅ Flask-Login初始化成功")

    except Exception as e:
        logger.error(f"Flask-Login初始化失败: {e}")

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

        # 初始化下载管理器
        from .core.download_manager import initialize_download_manager
        initialize_download_manager(app)
        logger.info("✅ 下载管理器初始化成功")

        # 自动数据库迁移
        _auto_migrate_database(app)

    except Exception as e:
        logger.error(f"应用初始化失败: {e}")

def _init_directories(app):
    """初始化目录（以 root 用户运行，简化处理）"""
    try:
        download_folder = app.config['DOWNLOAD_FOLDER']
        os.makedirs(download_folder, exist_ok=True)
        logger.info(f"下载目录已创建: {download_folder}")

        # 设置权限
        _fix_directory_permissions(download_folder)

        # 权限测试
        test_file = os.path.join(download_folder, '.write_test')
        if _test_directory_write(test_file, download_folder):
            logger.info(f"✅ 下载目录权限验证成功: {download_folder}")
        else:
            logger.warning(f"⚠️ 下载目录权限测试失败，但继续运行: {download_folder}")

    except Exception as e:
        logger.error(f"目录初始化失败: {e}")
        # 使用系统临时目录作为备用
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
        from .routes import main_bp, auth_bp, api_bp, admin_bp, shortcuts_bp, telegram_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(shortcuts_bp, url_prefix='/api/shortcuts')
        app.register_blueprint(telegram_bp, url_prefix='/telegram')

        logger.info("✅ 蓝图注册成功")

    except Exception as e:
        logger.error(f"蓝图注册失败: {e}")

def _auto_migrate_database(app):
    """自动数据库迁移 - 添加缺失的字段"""
    try:
        logger.info("🔍 检查数据库结构...")

        with app.app_context():
            from .models import db, TelegramConfig

            # 直接检查表结构，不依赖 ORM 查询
            try:
                with db.engine.connect() as conn:
                    from sqlalchemy import text

                    # 检查当前表结构
                    if db.engine.name == 'sqlite':
                        result = conn.execute(text("PRAGMA table_info(telegram_config)"))
                        columns = [row[1] for row in result.fetchall()]
                    else:
                        result = conn.execute(text("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'telegram_config'
                        """))
                        columns = [row[0] for row in result.fetchall()]

                    logger.info(f"📋 当前字段: {columns}")

                    # 检查是否需要添加字段
                    if 'api_id' in columns and 'api_hash' in columns:
                        logger.info("✅ API 字段已存在")
                        return

                    # 需要添加字段
                    logger.warning("⚠️ API 字段不存在，开始添加...")

            except Exception as check_error:
                logger.error(f"❌ 检查表结构失败: {check_error}")
                return

            # 添加缺失的字段
            try:
                with db.engine.connect() as conn:
                    from sqlalchemy import text

                    # 添加 api_id 字段
                    if 'api_id' not in columns:
                        if db.engine.name == 'sqlite':
                            conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_id VARCHAR(20)"))
                        else:
                            conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_id VARCHAR(20) NULL"))
                        logger.info("✅ 添加 api_id 字段成功")
                    else:
                        logger.info("ℹ️ api_id 字段已存在")

                    # 添加 api_hash 字段
                    if 'api_hash' not in columns:
                        if db.engine.name == 'sqlite':
                            conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_hash VARCHAR(50)"))
                        else:
                            conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_hash VARCHAR(50) NULL"))
                        logger.info("✅ 添加 api_hash 字段成功")
                    else:
                        logger.info("ℹ️ api_hash 字段已存在")

                    # 提交事务
                    conn.commit()

                logger.info("🎉 数据库迁移完成！")

            except Exception as migrate_error:
                logger.error(f"❌ 数据库迁移失败: {migrate_error}")
                # 不抛出异常，让应用继续启动

    except Exception as e:
        logger.error(f"❌ 数据库迁移检查失败: {e}")
        # 不抛出异常，让应用继续启动

# 为 gunicorn 提供应用工厂函数
def get_app():
    """获取应用实例（用于 gunicorn）"""
    return create_app()

# 为了兼容性，提供 app 变量（仅在直接运行时使用）
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False)
else:
    # 为 gunicorn 提供应用实例
    app = create_app()
