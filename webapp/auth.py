#!/usr/bin/env python3
"""
用户认证系统
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, redirect, url_for

class AuthManager:
    """认证管理器"""

    def __init__(self):
        # 默认管理员账号（可通过环境变量配置）
        self.admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        self.admin_password_hash = self._hash_password(
            os.environ.get('ADMIN_PASSWORD', 'admin123')
        )

        # 会话配置
        self.session_timeout_hours = 24

        # 存储活跃会话
        self.active_sessions = {}

    def _hash_password(self, password):
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_credentials(self, username, password):
        """验证用户凭据"""
        if username == self.admin_username:
            password_hash = self._hash_password(password)
            return password_hash == self.admin_password_hash
        return False

    def create_session(self, username):
        """创建用户会话"""
        session_token = secrets.token_urlsafe(32)
        session_data = {
            'username': username,
            'created_at': datetime.now(),
            'last_activity': datetime.now()
        }

        self.active_sessions[session_token] = session_data
        return session_token

    def verify_session(self, session_token):
        """验证会话有效性"""
        if not session_token or session_token not in self.active_sessions:
            return False

        session_data = self.active_sessions[session_token]

        # 检查会话是否过期
        if datetime.now() - session_data['created_at'] > timedelta(hours=self.session_timeout_hours):
            del self.active_sessions[session_token]
            return False

        # 更新最后活动时间
        session_data['last_activity'] = datetime.now()
        return True

    def get_session_user(self, session_token):
        """获取会话用户信息"""
        if session_token in self.active_sessions:
            return self.active_sessions[session_token]['username']
        return None

    def destroy_session(self, session_token):
        """销毁会话"""
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_tokens = []

        for token, session_data in self.active_sessions.items():
            if current_time - session_data['created_at'] > timedelta(hours=self.session_timeout_hours):
                expired_tokens.append(token)

        for token in expired_tokens:
            del self.active_sessions[token]

        return len(expired_tokens)

# 全局认证管理器
auth_manager = AuthManager()

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 统一的认证检查逻辑
        is_authenticated = False

        # 1. 优先检查 Authorization header
        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            if auth_manager.verify_session(token):
                is_authenticated = True

        # 2. 检查 Flask session
        if not is_authenticated and 'auth_token' in session:
            if auth_manager.verify_session(session['auth_token']):
                is_authenticated = True
            else:
                # 清理无效的session
                session.clear()

        if is_authenticated:
            return f(*args, **kwargs)

        # 未认证处理
        if request.path.startswith('/api/'):
            return jsonify({'error': '需要登录', 'code': 'AUTH_REQUIRED'}), 401

        # 对于页面请求，构建重定向URL
        redirect_url = url_for('auth.login')
        if request.path != '/login':
            redirect_url += f'?redirect={request.path}'

        return redirect(redirect_url)

    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 先检查登录
        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
        elif 'auth_token' in session:
            token = session['auth_token']
        else:
            if request.path.startswith('/api/'):
                return jsonify({'error': '需要登录', 'code': 'AUTH_REQUIRED'}), 401
            return redirect(url_for('auth.login'))

        if not auth_manager.verify_session(token):
            if request.path.startswith('/api/'):
                return jsonify({'error': '会话已过期', 'code': 'SESSION_EXPIRED'}), 401
            return redirect(url_for('auth.login'))

        # 检查是否为管理员
        username = auth_manager.get_session_user(token)
        if username != auth_manager.admin_username:
            if request.path.startswith('/api/'):
                return jsonify({'error': '需要管理员权限', 'code': 'ADMIN_REQUIRED'}), 403
            return jsonify({'error': '权限不足'}), 403

        return f(*args, **kwargs)

    return decorated_function

def get_current_user():
    """获取当前登录用户"""
    auth_token = request.headers.get('Authorization')
    if auth_token and auth_token.startswith('Bearer '):
        token = auth_token.split(' ')[1]
    elif 'auth_token' in session:
        token = session['auth_token']
    else:
        return None

    if auth_manager.verify_session(token):
        return auth_manager.get_session_user(token)

    return None
