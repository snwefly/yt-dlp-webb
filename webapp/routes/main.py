# -*- coding: utf-8 -*-
"""
主要页面路由
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
import logging
import os

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """主网页界面 - 公开访问，前端处理认证状态"""
    is_authenticated = current_user.is_authenticated
    user_data = current_user.username if is_authenticated else None
    is_admin = current_user.is_admin if is_authenticated else False

    logger.info(f"访问主页 - 用户: {user_data}, 管理员: {is_admin}")
    return render_template('index.html',
                         is_authenticated=is_authenticated,
                         current_user=user_data,
                         is_admin=is_admin)

@main_bp.route('/welcome')
def welcome():
    """公开的欢迎页面，引导用户登录"""
    return render_template('welcome.html')

@main_bp.route('/shortcuts-help')
def shortcuts_help():
    """iOS快捷指令使用指南 - 公开访问，前端处理认证状态"""
    is_authenticated = current_user.is_authenticated
    user_data = current_user.username if is_authenticated else None
    is_admin = current_user.is_admin if is_authenticated else False

    return render_template('shortcuts_help.html',
                         is_authenticated=is_authenticated,
                         current_user=user_data,
                         is_admin=is_admin)

@main_bp.route('/files')
def files():
    """文件管理页面 - 公开访问，前端处理认证状态"""
    is_authenticated = current_user.is_authenticated
    user_data = current_user.username if is_authenticated else None
    is_admin = current_user.is_admin if is_authenticated else False

    return render_template('files.html',
                         is_authenticated=is_authenticated,
                         current_user=user_data,
                         is_admin=is_admin)

@main_bp.route('/video-player')
def video_player():
    """视频播放器页面 - 独立页面，避免CSS冲突"""
    # 获取URL参数
    video_url = request.args.get('url')
    filename = request.args.get('filename', '未知视频')

    if not video_url:
        logger.warning("视频播放器访问缺少URL参数")
        return "缺少视频URL参数", 400

    logger.info(f"打开视频播放器 - 文件: {filename}")

    return render_template('video_player.html')



# 调试功能已移除 - 使用Flask-Login后不再需要复杂的session调试

# 测试路由已移除

@main_bp.route('/health')
def health_check():
    """健康检查端点"""
    try:
        # 检查 yt-dlp 可用性
        from ..core.ytdlp_manager import get_ytdlp_manager
        manager = get_ytdlp_manager()
        ytdlp_available = manager.is_available()

        # 检查下载目录
        download_dir = os.environ.get('DOWNLOAD_FOLDER', '/app/downloads')
        download_dir_writable = os.path.exists(download_dir) and os.access(download_dir, os.W_OK)

        # 基础健康状态
        health_status = {
            'status': 'healthy' if ytdlp_available and download_dir_writable else 'unhealthy',
            'timestamp': int(__import__('time').time()),
            'components': {
                'yt_dlp': {
                    'status': 'ok' if ytdlp_available else 'error',
                    'available': ytdlp_available
                },
                'download_directory': {
                    'status': 'ok' if download_dir_writable else 'error',
                    'path': download_dir,
                    'writable': download_dir_writable
                }
            }
        }

        # 尝试获取 yt-dlp 版本信息
        try:
            import yt_dlp
            health_status['components']['yt_dlp']['version'] = yt_dlp.__version__
        except Exception:
            health_status['components']['yt_dlp']['version'] = 'unknown'

        # 返回适当的状态码
        status_code = 200 if health_status['status'] == 'healthy' else 503

        logger.debug(f"健康检查结果: {health_status['status']}")
        return jsonify(health_status), status_code

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': int(__import__('time').time()),
            'error': str(e)
        }), 500

# 测试路由已删除

@main_bp.route('/debug-db')
def debug_db():
    """数据库调试信息"""
    try:
        from ..models import db, User

        # 检查数据库连接
        db_info = {
            'database_uri': current_app.config.get('SQLALCHEMY_DATABASE_URI'),
            'tables': [],
            'users': []
        }

        # 检查表是否存在
        try:
            inspector = db.inspect(db.engine)
            db_info['tables'] = inspector.get_table_names()
        except Exception as e:
            db_info['table_error'] = str(e)

        # 检查用户
        try:
            users = User.query.all()
            for user in users:
                db_info['users'].append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_admin': user.is_admin,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                })
        except Exception as e:
            db_info['users_error'] = str(e)

        return jsonify(db_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/init-db')
def init_db():
    """强制初始化数据库"""
    try:
        from ..models import db, User

        # 创建所有表
        db.create_all()

        # 检查是否已有管理员用户
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            # 创建管理员用户
            admin_user = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': '数据库初始化成功，管理员用户已创建',
                'admin_user': {
                    'username': admin_user.username,
                    'email': admin_user.email,
                    'is_admin': admin_user.is_admin
                }
            })
        else:
            return jsonify({
                'success': True,
                'message': '数据库已存在，管理员用户已存在',
                'admin_user': {
                    'username': admin_user.username,
                    'email': admin_user.email,
                    'is_admin': admin_user.is_admin
                }
            })

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@main_bp.route('/migrate-telegram-api')
def migrate_telegram_api():
    """迁移 Telegram API 字段"""
    try:
        from ..models import db

        # 检查当前表结构
        with db.engine.connect() as conn:
            # 检查字段是否已存在
            from sqlalchemy import text
            result = conn.execute(text("PRAGMA table_info(telegram_config)"))
            columns = [row[1] for row in result.fetchall()]

            messages = []

            # 添加 api_id 字段
            if 'api_id' not in columns:
                conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_id VARCHAR(20)"))
                messages.append("✅ 添加 api_id 字段成功")
            else:
                messages.append("ℹ️ api_id 字段已存在")

            # 添加 api_hash 字段
            if 'api_hash' not in columns:
                conn.execute(text("ALTER TABLE telegram_config ADD COLUMN api_hash VARCHAR(50)"))
                messages.append("✅ 添加 api_hash 字段成功")
            else:
                messages.append("ℹ️ api_hash 字段已存在")

            # 提交更改
            conn.commit()

            # 验证字段
            result = conn.execute(text("PRAGMA table_info(telegram_config)"))
            new_columns = [row[1] for row in result.fetchall()]

            return jsonify({
                'success': True,
                'message': '数据库迁移完成',
                'details': messages,
                'columns_before': columns,
                'columns_after': new_columns
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500





