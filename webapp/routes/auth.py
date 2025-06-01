# -*- coding: utf-8 -*-
"""
认证相关路由
"""

from flask import Blueprint, render_template, request, jsonify, session
from ..auth import auth_manager, login_required, admin_required
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    """登录页面"""
    return render_template('login.html')

@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """用户登录API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)

        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400

        # 验证用户凭据
        if auth_manager.verify_credentials(username, password):
            # 创建会话
            token = auth_manager.create_session(username)

            # 设置session为permanent，确保长期有效
            session.permanent = True
            session['auth_token'] = token

            logger.info(f"用户 {username} 登录成功")

            return jsonify({
                'success': True,
                'message': '登录成功',
                'token': token,
                'username': username
            })
        else:
            logger.warning(f"用户 {username} 登录失败：凭据无效")
            return jsonify({'error': '用户名或密码错误'}), 401

    except Exception as e:
        logger.error(f"登录过程中发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """用户登出API"""
    try:
        # 获取会话token
        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            auth_manager.destroy_session(token)

        # 清除session
        if 'auth_token' in session:
            auth_manager.destroy_session(session['auth_token'])
            session.clear()

        return jsonify({'success': True, 'message': '登出成功'})

    except Exception as e:
        logger.error(f"登出过程中发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/verify', methods=['GET'])
def api_verify():
    """验证会话有效性"""
    try:
        # 检查会话token
        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            if auth_manager.verify_session(token):
                username = auth_manager.get_session_user(token)
                return jsonify({
                    'valid': True,
                    'username': username,
                    'is_admin': username == auth_manager.admin_username
                })

        # 检查session
        if 'auth_token' in session:
            if auth_manager.verify_session(session['auth_token']):
                username = auth_manager.get_session_user(session['auth_token'])
                return jsonify({
                    'valid': True,
                    'username': username,
                    'is_admin': username == auth_manager.admin_username
                })

        return jsonify({'valid': False}), 401

    except Exception as e:
        logger.error(f"会话验证过程中发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/sync-session', methods=['POST'])
def api_sync_session():
    """同步localStorage token到Flask session"""
    try:
        # 获取Authorization header中的token
        auth_token = request.headers.get('Authorization')
        if not auth_token or not auth_token.startswith('Bearer '):
            return jsonify({'error': '无效的Authorization header'}), 400

        token = auth_token.split(' ')[1]

        # 验证token有效性
        if not auth_manager.verify_session(token):
            return jsonify({'error': 'Token无效'}), 401

        # 将token同步到Flask session
        session.permanent = True
        session['auth_token'] = token

        username = auth_manager.get_session_user(token)
        logger.info(f"✅ Token已同步到Flask session - 用户: {username}")

        return jsonify({
            'success': True,
            'message': 'Session同步成功',
            'username': username,
            'is_admin': username == auth_manager.admin_username
        })

    except Exception as e:
        logger.error(f"Session同步失败: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/session-info', methods=['GET'])
def api_session_info():
    """获取会话详细信息"""
    try:
        # 检查会话token
        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            session_info = auth_manager.get_session_info(token)
            if session_info:
                return jsonify({
                    'success': True,
                    'session_info': session_info
                })

        # 检查session
        if 'auth_token' in session:
            session_info = auth_manager.get_session_info(session['auth_token'])
            if session_info:
                return jsonify({
                    'success': True,
                    'session_info': session_info
                })

        return jsonify({'error': '无效的会话'}), 401

    except Exception as e:
        logger.error(f"获取会话信息时发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/change-password', methods=['POST'])
def api_change_password():
    """修改密码"""
    try:
        # 检查认证
        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            if not auth_manager.verify_session(token):
                return jsonify({'error': '会话无效'}), 401
            username = auth_manager.get_session_user(token)
        elif 'auth_token' in session:
            if not auth_manager.verify_session(session['auth_token']):
                return jsonify({'error': '会话无效'}), 401
            username = auth_manager.get_session_user(session['auth_token'])
        else:
            return jsonify({'error': '未登录'}), 401

        # 只有管理员可以修改密码
        if username != auth_manager.admin_username:
            return jsonify({'error': '权限不足'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            return jsonify({'error': '所有字段都是必填的'}), 400

        # 验证当前密码
        if not auth_manager.verify_credentials(username, current_password):
            return jsonify({'error': '当前密码错误'}), 400

        # 验证新密码确认
        if new_password != confirm_password:
            return jsonify({'error': '新密码和确认密码不匹配'}), 400

        # 密码强度验证
        if len(new_password) < 6:
            return jsonify({'error': '新密码长度至少6位'}), 400

        # 修改密码
        if auth_manager.change_password(username, new_password):
            logger.info(f"用户 {username} 成功修改密码")
            return jsonify({
                'success': True,
                'message': '密码修改成功'
            })
        else:
            return jsonify({'error': '密码修改失败'}), 500

    except Exception as e:
        logger.error(f"修改密码时发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/api/auth/clear-all-sessions', methods=['POST'])
@admin_required
def api_clear_all_sessions():
    """清除所有会话"""
    try:
        from ..auth import get_current_user
        username = get_current_user()

        # 清除所有会话
        cleared_count = auth_manager.clear_all_sessions()

        logger.info(f"管理员 {username} 清除了所有会话，共清除 {cleared_count} 个会话")

        return jsonify({
            'success': True,
            'message': f'已清除 {cleared_count} 个会话',
            'cleared_count': cleared_count
        })

    except Exception as e:
        logger.error(f"清除所有会话时发生错误: {e}")
        return jsonify({'error': str(e)}), 500
