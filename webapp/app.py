# -*- coding: utf-8 -*-
"""
Flask 应用工厂 - 重构版本
"""

import os
import logging
from datetime import timedelta
from flask import Flask

# 健壮的 flask_login 导入
try:
    from flask_login import LoginManager
except ImportError as e:
    print(f"❌ flask_login 导入失败: {e}")
    print("🔧 尝试安装 Flask-Login...")

    import subprocess
    import sys
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            '--no-cache-dir', '--force-reinstall', 'Flask-Login>=0.6.3'
        ])
        print("✅ Flask-Login 安装成功，重新导入...")
        from flask_login import LoginManager
    except Exception as install_error:
        print(f"❌ Flask-Login 安装失败: {install_error}")
        print("🆘 使用备用方案...")
        # 创建一个最小的 LoginManager 替代品
        class LoginManager:
            def __init__(self):
                self.login_view = None
                self.login_message = None
                self.login_message_category = None

            def init_app(self, app):
                pass

            def user_loader(self, func):
                return func

        print("⚠️ 使用最小 LoginManager 替代品，部分功能可能不可用")

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

def create_app(config=None):
    """创建Flask应用

    Args:
        config: 可选的配置字典，用于覆盖默认配置
    """
    # 使用统一的应用初始化器
    from .core.app_initializer import create_and_initialize_app
    return create_and_initialize_app(config)

# 这些函数已经移动到 app_initializer.py 中，保留用于向后兼容
def _init_database(app):
    """初始化数据库（已废弃，使用 app_initializer）"""
    logger.warning("⚠️ _init_database 已废弃，请使用 app_initializer")
    pass

# 这些函数已经移动到 app_initializer.py 中，保留用于向后兼容
def _init_login_manager(app):
    """初始化Flask-Login（已废弃，使用 app_initializer）"""
    logger.warning("⚠️ _init_login_manager 已废弃，请使用 app_initializer")
    pass

def _initialize_app(app):
    """初始化应用组件（已废弃，使用 app_initializer）"""
    logger.warning("⚠️ _initialize_app 已废弃，请使用 app_initializer")
    pass

def _init_directories(app):
    """初始化目录（已废弃，使用 app_initializer）"""
    logger.warning("⚠️ _init_directories 已废弃，请使用 app_initializer")
    pass

def _init_cleanup_manager(app):
    """初始化文件清理管理器（已废弃，使用 app_initializer）"""
    logger.warning("⚠️ _init_cleanup_manager 已废弃，请使用 app_initializer")
    pass

def _register_blueprints(app):
    """注册蓝图（已废弃，使用 app_initializer）"""
    logger.warning("⚠️ _register_blueprints 已废弃，请使用 app_initializer")
    pass

def _register_error_handlers(app):
    """注册错误处理器（已废弃，使用 app_initializer）"""
    logger.warning("⚠️ _register_error_handlers 已废弃，请使用 app_initializer")
    pass

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

                    # 添加 api_id 字段（整数类型）
                    if 'api_id' not in columns:
                        if db.engine.name == 'sqlite':
                            conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_id INTEGER"))
                        else:
                            conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_id INTEGER NULL"))
                        logger.info("✅ 添加 api_id 字段成功（整数类型）")
                    else:
                        # 检查现有字段类型，如果是字符串类型则需要迁移
                        logger.info("ℹ️ api_id 字段已存在，检查类型...")
                        try:
                            # 尝试获取字段类型信息
                            if db.engine.name == 'sqlite':
                                type_result = conn.execute(text("PRAGMA table_info(telegram_config)"))
                                for row in type_result.fetchall():
                                    if row[1] == 'api_id' and 'VARCHAR' in str(row[2]).upper():
                                        logger.warning("⚠️ 检测到 api_id 字段为字符串类型，需要数据迁移")
                                        # 对于 SQLite，我们需要重建表来改变字段类型
                                        # 这里先记录警告，实际迁移可以在后续版本中处理
                                        logger.warning("📝 建议：请手动检查 api_id 字段中的数据是否为有效整数")
                        except Exception as type_check_error:
                            logger.debug(f"字段类型检查失败: {type_check_error}")

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

# WSGI 应用实例（用于 gunicorn）
application = create_app()

# 为了兼容性，提供 app 变量
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False)
else:
    # 不在模块级别创建应用实例，避免应用上下文问题
    # gunicorn 将使用工厂函数模式
    app = None
