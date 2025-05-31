#!/usr/bin/env python3
"""
用户认证系统
"""

import os
import hashlib
import secrets
import logging
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session, redirect, url_for

logger = logging.getLogger(__name__)

class AuthManager:
    """认证管理器"""

    def __init__(self):
        # 默认管理员账号（可通过环境变量配置）
        self.admin_username = os.environ.get('ADMIN_USERNAME', 'admin')

        # 密码配置文件路径
        self.password_config_file = '/app/config/admin_password.json'

        # 加载密码（优先从配置文件，然后从环境变量）
        self.admin_password_hash = self._load_password()

        # 会话配置 - 支持环境变量配置
        # 默认30天，可通过环境变量 SESSION_TIMEOUT_DAYS 配置
        timeout_days = int(os.environ.get('SESSION_TIMEOUT_DAYS', '30'))
        self.session_timeout_hours = timeout_days * 24

        # 也支持直接设置小时数 SESSION_TIMEOUT_HOURS（优先级更高）
        if 'SESSION_TIMEOUT_HOURS' in os.environ:
            self.session_timeout_hours = int(os.environ.get('SESSION_TIMEOUT_HOURS'))

        # 最小1小时，最大365天
        self.session_timeout_hours = max(1, min(self.session_timeout_hours, 365 * 24))

        # 活动延长配置 - 每次活动是否延长会话
        self.extend_on_activity = os.environ.get('EXTEND_SESSION_ON_ACTIVITY', 'true').lower() == 'true'

        # 活动延长的最大时间（小时）- 防止会话无限延长
        self.max_extension_hours = int(os.environ.get('MAX_SESSION_EXTENSION_HOURS', str(self.session_timeout_hours)))

        # 存储活跃会话
        self.active_sessions = {}

    def _hash_password(self, password):
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _load_password(self):
        """加载密码（优先从配置文件，然后从环境变量）"""
        try:
            # 尝试从配置文件加载
            if os.path.exists(self.password_config_file):
                with open(self.password_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'password_hash' in config:
                        logger.info("从配置文件加载管理员密码")
                        return config['password_hash']
        except Exception as e:
            logger.warning(f"加载密码配置文件失败: {e}")

        # 从环境变量加载
        password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        logger.info("从环境变量加载管理员密码")
        return self._hash_password(password)

    def _save_password(self, password_hash):
        """保存密码到配置文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.password_config_file), exist_ok=True)

            config = {
                'password_hash': password_hash,
                'updated_at': datetime.now().isoformat(),
                'updated_by': self.admin_username
            }

            with open(self.password_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info("密码已保存到配置文件")
            return True
        except Exception as e:
            logger.error(f"保存密码配置文件失败: {e}")
            return False

    def verify_credentials(self, username, password):
        """验证用户凭据"""
        if username == self.admin_username:
            password_hash = self._hash_password(password)
            return password_hash == self.admin_password_hash
        return False

    def change_password(self, username, new_password):
        """修改密码"""
        if username == self.admin_username:
            # 生成新的密码哈希
            new_password_hash = self._hash_password(new_password)

            # 保存到配置文件
            if self._save_password(new_password_hash):
                # 更新内存中的密码哈希
                self.admin_password_hash = new_password_hash
                logger.info(f"管理员密码已永久更新")
                return True
            else:
                logger.error("密码保存失败")
                return False
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
        current_time = datetime.now()

        # 检查会话是否过期
        session_age = current_time - session_data['created_at']
        if session_age > timedelta(hours=self.session_timeout_hours):
            del self.active_sessions[session_token]
            return False

        # 如果启用活动延长，检查是否需要延长会话
        if self.extend_on_activity:
            # 检查会话是否已经延长太久
            if session_age <= timedelta(hours=self.max_extension_hours):
                # 如果距离上次活动超过1小时，则延长会话
                time_since_activity = current_time - session_data['last_activity']
                if time_since_activity > timedelta(hours=1):
                    # 重置创建时间，相当于延长会话
                    session_data['created_at'] = current_time - timedelta(hours=1)

        # 更新最后活动时间
        session_data['last_activity'] = current_time
        return True

    def get_session_user(self, session_token):
        """获取会话用户信息"""
        if session_token in self.active_sessions:
            return self.active_sessions[session_token]['username']
        return None

    def get_session_info(self, session_token):
        """获取会话详细信息"""
        if session_token not in self.active_sessions:
            return None

        session_data = self.active_sessions[session_token]
        current_time = datetime.now()

        # 计算会话剩余时间
        session_age = current_time - session_data['created_at']
        remaining_time = timedelta(hours=self.session_timeout_hours) - session_age

        return {
            'username': session_data['username'],
            'created_at': session_data['created_at'].isoformat(),
            'last_activity': session_data['last_activity'].isoformat(),
            'session_age_hours': round(session_age.total_seconds() / 3600, 2),
            'remaining_hours': max(0, round(remaining_time.total_seconds() / 3600, 2)),
            'timeout_hours': self.session_timeout_hours,
            'extend_on_activity': self.extend_on_activity,
            'max_extension_hours': self.max_extension_hours
        }

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
