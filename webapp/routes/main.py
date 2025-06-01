# -*- coding: utf-8 -*-
"""
主要页面路由
"""

from flask import Blueprint, render_template, jsonify, request
from ..auth import login_required
import logging
import os

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """主网页界面"""
    # 不强制要求登录，但会传递认证状态给模板
    from flask import session
    from ..auth import auth_manager

    # 检查session中的认证状态
    current_user = None
    is_authenticated = False

    if 'auth_token' in session:
        token = session['auth_token']
        if auth_manager.verify_session(token):
            current_user = auth_manager.get_session_user(token)
            is_authenticated = True
            logger.info(f"访问主页 - 用户已通过session认证: {current_user}")
        else:
            # 清除无效的session
            session.pop('auth_token', None)
            logger.info("访问主页 - session中的token无效，已清除")
    else:
        logger.info("访问主页 - 未找到session认证信息")

    logger.info(f"访问主页 - 最终认证状态: {is_authenticated}, 用户: {current_user}")
    return render_template('index.html', is_authenticated=is_authenticated, current_user=current_user)

@main_bp.route('/shortcuts-help')
@login_required
def shortcuts_help():
    """iOS快捷指令使用指南"""
    from ..auth import get_current_user

    current_user = get_current_user()
    is_authenticated = current_user is not None

    return render_template('shortcuts_help.html', is_authenticated=is_authenticated, current_user=current_user)

@main_bp.route('/files')
@login_required
def files():
    """文件管理页面"""
    from ..auth import get_current_user

    current_user = get_current_user()
    is_authenticated = current_user is not None

    return render_template('files.html', is_authenticated=is_authenticated, current_user=current_user)



@main_bp.route('/debug')
def debug():
    """认证调试页面"""
    from flask import session
    from ..auth import auth_manager

    # 收集调试信息
    debug_info = {
        'session_data': dict(session),
        'session_has_auth_token': 'auth_token' in session,
        'session_auth_token': session.get('auth_token', 'None')[:20] + '...' if session.get('auth_token') else 'None',
        'session_permanent': session.permanent,
        'request_headers': dict(request.headers),
        'auth_manager_sessions': len(auth_manager.active_sessions),
        'sessions_file_exists': os.path.exists(auth_manager.sessions_file),
        'sessions_file_path': auth_manager.sessions_file
    }

    # 检查session token有效性
    if 'auth_token' in session:
        token = session['auth_token']
        debug_info['session_token_valid'] = auth_manager.verify_session(token)
        debug_info['session_token_user'] = auth_manager.get_session_user(token) if auth_manager.verify_session(token) else 'None'
    else:
        debug_info['session_token_valid'] = False
        debug_info['session_token_user'] = 'None'

    return render_template('debug_auth.html', debug_info=debug_info)

@main_bp.route('/test-auth')
def test_auth():
    """简单的认证测试端点"""
    from flask import session
    from ..auth import auth_manager

    result = {
        'timestamp': __import__('time').time(),
        'flask_session_has_token': 'auth_token' in session,
        'active_sessions_count': len(auth_manager.active_sessions),
        'sessions_file_exists': os.path.exists(auth_manager.sessions_file)
    }

    if 'auth_token' in session:
        token = session['auth_token']
        result['token_valid'] = auth_manager.verify_session(token)
        result['token_user'] = auth_manager.get_session_user(token)

    return jsonify(result)

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

@main_bp.route('/auth-test')
def auth_test():
    """认证状态测试页面"""
    from ..auth import get_current_user

    current_user = get_current_user()
    is_authenticated = current_user is not None

    return render_template('auth_test.html', is_authenticated=is_authenticated, current_user=current_user)

@main_bp.route('/admin-check')
def admin_check():
    """检查管理员权限状态"""
    from flask import session
    from ..auth import auth_manager

    result = {
        'timestamp': __import__('time').time(),
        'session_has_token': 'auth_token' in session,
        'admin_username': auth_manager.admin_username,
        'current_user': None,
        'is_admin': False,
        'token_valid': False
    }

    if 'auth_token' in session:
        token = session['auth_token']
        result['token_valid'] = auth_manager.verify_session(token)
        if result['token_valid']:
            current_user = auth_manager.get_session_user(token)
            result['current_user'] = current_user
            result['is_admin'] = (current_user == auth_manager.admin_username)

    return jsonify(result)





