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
    
    def _hash_password(self, password, salt=None):
        """密码哈希 - 使用 PBKDF2-HMAC-SHA256"""
        # 在真实应用中，salt 应该是随机生成并与哈希一起存储的
        # 为了简化环境变量配置，这里使用固定 salt 或从环境变量读取
        # 强烈建议为每个密码使用唯一的随机 salt
        iterations = 260000  # NIST 推荐的最小迭代次数
        dklen = 64  # 期望的派生密钥长度（字节）
        
        # 如果没有提供 salt，则使用环境变量或固定值
        # 注意：为所有密码使用相同的 salt 会降低安全性。
        # 更好的做法是生成一个随机 salt，并将其与哈希一起存储。
        # 例如：salt = secrets.token_bytes(16)
        # 然后存储 salt.hex() + ':' + hashed_password.hex()
        
        # 为了此示例，我们将使用一个固定的 salt 或从环境变量获取
        # 这仍然比单次 SHA256 强得多
        _salt_str = os.environ.get('PASSWORD_SALT', "a_default_fixed_salt_for_this_app")
        _salt = _salt_str.encode('utf-8')

        hashed_password = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            _salt,
            iterations,
            dklen=dklen
        )
        return hashed_password.hex() # 返回十六进制编码的哈希

    def verify_credentials(self, username, password):
        """验证用户凭据"""
        if username == self.admin_username:
            # 假设 self.admin_password_hash 是使用上述 _hash_password 方法生成的
            password_hash_to_check = self._hash_password(password)
            return password_hash_to_check == self.admin_password_hash
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
        
        # 检查会话是否过期 (基于最后活动时间)
        if datetime.now() - session_data.get('last_activity', session_data['created_at']) > \
           timedelta(hours=self.session_timeout_hours):
            if session_token in self.active_sessions: # 再次检查以防并发删除
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
        
        for token, data in list(self.active_sessions.items()): # 使用 list() 避免在迭代时修改字典
            if current_time - data.get('last_activity', data['created_at']) > \
               timedelta(hours=self.session_timeout_hours):
                expired_tokens.append(token)
        
        for token in expired_tokens:
            if token in self.active_sessions: # 再次检查以防并发删除
                 del self.active_sessions[token]
        
        return len(expired_tokens)

# 全局认证管理器
auth_manager = AuthManager()

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查会话token
        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            if auth_manager.verify_session(token):
                return f(*args, **kwargs)
        
        # 检查session
        if 'auth_token' in session:
            if auth_manager.verify_session(session['auth_token']):
                return f(*args, **kwargs)
        
        # 对于API请求返回JSON错误
        if request.path.startswith('/api/'):
            return jsonify({'error': '需要登录', 'code': 'AUTH_REQUIRED'}), 401
        
        # 对于页面请求重定向到登录页
        return redirect(url_for('login'))
    
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
            return redirect(url_for('login'))
        
        if not auth_manager.verify_session(token):
            if request.path.startswith('/api/'):
                return jsonify({'error': '会话已过期', 'code': 'SESSION_EXPIRED'}), 401
            return redirect(url_for('login'))
        
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
