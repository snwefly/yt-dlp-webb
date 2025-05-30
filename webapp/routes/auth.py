# -*- coding: utf-8 -*-
"""
认证相关路由
"""

from flask import Blueprint, render_template, request, jsonify, session
from ..auth import auth_manager, login_required
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
