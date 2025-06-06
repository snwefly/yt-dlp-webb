"""
应用初始化器 - 统一的应用组件初始化逻辑
"""

import os
import logging
from datetime import timedelta
from flask import Flask
from flask_login import LoginManager

logger = logging.getLogger(__name__)

class AppInitializer:
    """应用初始化器，负责统一管理应用组件的初始化"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.initialized_components = set()
    
    def initialize_all(self, config=None):
        """初始化所有组件"""
        try:
            # 1. 配置应用
            self._configure_app(config)
            
            # 2. 配置日志
            self._configure_logging()
            
            # 3. 初始化服务注册中心
            self._initialize_service_registry()
            
            # 4. 在应用上下文中初始化组件
            with self.app.app_context():
                self._initialize_database()
                self._initialize_login_manager()
                self._initialize_core_services()
                self._initialize_directories()
                self._auto_migrate_database()
            
            # 5. 注册蓝图和错误处理器
            self._register_blueprints()
            self._register_error_handlers()
            
            logger.info("✅ 应用初始化完成")
            
        except Exception as e:
            logger.error(f"应用初始化失败: {e}")
            raise
    
    def _configure_app(self, config=None):
        """配置应用"""
        if 'app_config' in self.initialized_components:
            return
        
        # 使用配置管理器
        from .config_manager import get_flask_config, get_config
        
        # 配置应用
        self.app.config.update(get_flask_config())
        self.app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=get_config('SESSION_TIMEOUT_DAYS'))
        
        # 应用自定义配置（如果提供）
        if config:
            self.app.config.update(config)
            logger.info(f"✅ 应用了自定义配置: {list(config.keys())}")
        
        self.initialized_components.add('app_config')
        logger.info("✅ 应用配置完成")
    
    def _configure_logging(self):
        """配置日志"""
        if 'logging' in self.initialized_components:
            return
        
        # 配置日志 - 确保输出到容器日志
        if not self.app.debug:
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

            self.app.logger.info('🚀 Flask 应用已启动，日志系统已配置')

        # 设置日志
        if not self.app.debug:
            logging.basicConfig(level=logging.INFO)
        
        self.initialized_components.add('logging')
        logger.info("✅ 日志配置完成")
    
    def _initialize_service_registry(self):
        """初始化服务注册中心"""
        if 'service_registry' in self.initialized_components:
            return
        
        from .service_registry import initialize_core_services
        initialize_core_services(self.app)
        
        self.initialized_components.add('service_registry')
        logger.info("✅ 服务注册中心初始化完成")
    
    def _initialize_database(self):
        """初始化数据库"""
        if 'database' in self.initialized_components:
            return
        
        try:
            from ..models import db
            from .config_manager import get_config

            # 配置数据库 - 使用配置管理器
            db_path = get_config('DATABASE_PATH')
            self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
            self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            logger.info(f"数据库路径: {db_path}")

            # 初始化数据库
            db.init_app(self.app)

            # 创建表（已经在应用上下文中）
            db.create_all()

            # 创建默认数据
            self._create_default_data(db)

            self.initialized_components.add('database')
            logger.info("✅ 数据库初始化成功")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise
    
    def _create_default_data(self, db):
        """创建默认数据"""
        from ..models import User, TelegramConfig
        
        # 创建默认管理员用户
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
    
    def _initialize_login_manager(self):
        """初始化Flask-Login"""
        if 'login_manager' in self.initialized_components:
            return
        
        try:
            login_manager = LoginManager()
            login_manager.init_app(self.app)
            login_manager.login_view = 'auth.login'
            login_manager.login_message = '请先登录以访问此页面。'
            login_manager.login_message_category = 'info'

            @login_manager.user_loader
            def load_user(user_id):
                from ..models import User
                return User.query.get(int(user_id))

            self.initialized_components.add('login_manager')
            logger.info("✅ Flask-Login初始化成功")

        except Exception as e:
            logger.error(f"Flask-Login初始化失败: {e}")
            raise
    
    def _initialize_core_services(self):
        """初始化核心服务"""
        if 'core_services' in self.initialized_components:
            return
        
        try:
            # 初始化 yt-dlp
            from .ytdlp_manager import initialize_ytdlp
            if initialize_ytdlp():
                logger.info("✅ yt-dlp 初始化成功")
            else:
                logger.warning("⚠️ yt-dlp 初始化失败，但应用将继续运行")

            # 初始化文件清理管理器
            self._initialize_file_cleaner()

            self.initialized_components.add('core_services')
            logger.info("✅ 核心服务初始化成功")

        except Exception as e:
            logger.error(f"核心服务初始化失败: {e}")
            raise
    
    def _initialize_file_cleaner(self):
        """初始化文件清理管理器"""
        try:
            from ..file_cleaner import initialize_cleanup_manager
            from .config_manager import get_config, get_cleanup_config

            cleanup_config = get_cleanup_config()
            download_folder = get_config('DOWNLOAD_FOLDER')
            
            initialize_cleanup_manager(download_folder, cleanup_config)
            logger.info("✅ 文件清理管理器初始化成功")

        except Exception as e:
            logger.error(f"文件清理管理器初始化失败: {e}")
    
    def _initialize_directories(self):
        """初始化目录"""
        if 'directories' in self.initialized_components:
            return
        
        try:
            from .config_manager import config
            config.ensure_directories()
            
            # 权限测试
            download_folder = config.get('DOWNLOAD_FOLDER')
            test_file = os.path.join(download_folder, '.write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logger.info(f"✅ 目录权限验证成功: {download_folder}")
            except Exception as e:
                logger.warning(f"⚠️ 目录权限测试失败: {e}")

            self.initialized_components.add('directories')
            logger.info("✅ 目录初始化完成")

        except Exception as e:
            logger.error(f"目录初始化失败: {e}")
    
    def _auto_migrate_database(self):
        """自动数据库迁移"""
        if 'database_migration' in self.initialized_components:
            return
        
        # 这里可以调用现有的迁移逻辑
        from ..app import _auto_migrate_database
        _auto_migrate_database(self.app)
        
        self.initialized_components.add('database_migration')
    
    def _register_blueprints(self):
        """注册蓝图"""
        if 'blueprints' in self.initialized_components:
            return
        
        try:
            from ..routes import main_bp, auth_bp, api_bp, admin_bp, shortcuts_bp, telegram_bp

            self.app.register_blueprint(main_bp)
            self.app.register_blueprint(auth_bp)
            self.app.register_blueprint(api_bp, url_prefix='/api')
            self.app.register_blueprint(admin_bp, url_prefix='/admin')
            self.app.register_blueprint(shortcuts_bp, url_prefix='/api/shortcuts')
            self.app.register_blueprint(telegram_bp, url_prefix='/telegram')

            self.initialized_components.add('blueprints')
            logger.info("✅ 蓝图注册成功")

        except Exception as e:
            logger.error(f"蓝图注册失败: {e}")
            raise
    
    def _register_error_handlers(self):
        """注册错误处理器"""
        if 'error_handlers' in self.initialized_components:
            return
        
        try:
            from .error_handler import register_error_handlers
            register_error_handlers(self.app)
            
            self.initialized_components.add('error_handlers')
            logger.info("✅ 错误处理器注册成功")
            
        except Exception as e:
            logger.error(f"错误处理器注册失败: {e}")

def create_and_initialize_app(config=None) -> Flask:
    """创建并初始化应用的便捷函数"""
    app = Flask(__name__)
    initializer = AppInitializer(app)
    initializer.initialize_all(config)
    return app
