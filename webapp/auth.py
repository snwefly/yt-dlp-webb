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

        # 配置目录
        self.config_dir = '/app/config'

        # 密码配置文件路径
        self.password_config_file = os.path.join(self.config_dir, 'admin_password.json')

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

        # 存储活跃会话 - 使用持久化文件存储
        self.sessions_file = os.path.join(self.config_dir, 'sessions.json')

        # 确保配置目录存在
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            logger.info(f"✅ 配置目录已创建: {self.config_dir}")

            # 测试目录写权限
            test_file = os.path.join(self.config_dir, '.test_write')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info(f"✅ 配置目录写权限正常")

        except Exception as e:
            logger.error(f"❌ 配置目录创建失败: {e}")
            # 如果配置目录创建失败，使用临时目录
            import tempfile
            self.config_dir = tempfile.gettempdir()
            self.sessions_file = os.path.join(self.config_dir, 'yt-dlp-sessions.json')
            self.password_config_file = os.path.join(self.config_dir, 'yt-dlp-password.json')
            logger.warning(f"⚠️ 使用临时目录: {self.config_dir}")

        self.active_sessions = self._load_sessions()

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

    def _load_sessions(self):
        """从文件加载会话数据"""
        try:
            if os.path.exists(self.sessions_file):
                logger.info(f"🔄 从文件加载会话: {self.sessions_file}")
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)

                # 转换时间字符串为datetime对象
                for token, session_data in sessions_data.items():
                    if 'created_at' in session_data:
                        session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                    if 'last_activity' in session_data:
                        session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])

                logger.info(f"✅ 从文件加载了 {len(sessions_data)} 个会话")
                return sessions_data
            else:
                logger.info(f"📝 会话文件不存在，创建新的会话存储: {self.sessions_file}")
        except Exception as e:
            logger.error(f"❌ 加载会话文件失败: {e}")

        return {}

    def _save_sessions(self):
        """保存会话数据到文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.sessions_file), exist_ok=True)

            # 转换datetime对象为字符串
            sessions_data = {}
            for token, session_data in self.active_sessions.items():
                sessions_data[token] = {
                    'username': session_data['username'],
                    'created_at': session_data['created_at'].isoformat(),
                    'last_activity': session_data['last_activity'].isoformat()
                }

            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 保存了 {len(sessions_data)} 个会话到文件: {self.sessions_file}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存会话文件失败: {e}")
            logger.error(f"文件路径: {self.sessions_file}")
            logger.error(f"目录权限: {os.access(os.path.dirname(self.sessions_file), os.W_OK) if os.path.exists(os.path.dirname(self.sessions_file)) else '目录不存在'}")
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
        # 保存到文件
        self._save_sessions()
        logger.info(f"创建会话: {session_token[:20]}... 用户: {username}")
        return session_token

    def verify_session(self, session_token):
        """验证会话有效性"""
        if not session_token:
            logger.debug("🔍 会话验证失败: 无session_token")
            return False

        if session_token not in self.active_sessions:
            logger.debug(f"🔍 会话验证失败: token不存在 {session_token[:20]}...")
            return False

        session_data = self.active_sessions[session_token]
        current_time = datetime.now()

        # 检查会话是否过期
        session_age = current_time - session_data['created_at']
        if session_age > timedelta(hours=self.session_timeout_hours):
            logger.debug(f"🔍 会话验证失败: 会话过期 {session_age} > {self.session_timeout_hours}小时")
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
        # 保存到文件
        self._save_sessions()
        logger.debug(f"✅ 会话验证成功: {session_token[:20]}... 用户: {session_data['username']}")
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
            # 保存到文件
            self._save_sessions()
            logger.info(f"销毁会话: {session_token[:20]}...")

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_tokens = []

        for token, session_data in self.active_sessions.items():
            if current_time - session_data['created_at'] > timedelta(hours=self.session_timeout_hours):
                expired_tokens.append(token)

        for token in expired_tokens:
            del self.active_sessions[token]

        if expired_tokens:
            # 保存到文件
            self._save_sessions()
            logger.info(f"清理了 {len(expired_tokens)} 个过期会话")

        return len(expired_tokens)

    def clear_all_sessions(self):
        """清除所有会话"""
        session_count = len(self.active_sessions)
        self.active_sessions.clear()
        # 保存到文件
        self._save_sessions()
        logger.info(f"清除了所有 {session_count} 个会话")
        return session_count

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
        logger.debug(f"🔐 认证检查 - 路径: {request.path}, Authorization头: {auth_token[:50] if auth_token else 'None'}...")

        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            logger.debug(f"🔑 提取token: {token[:20]}...")
            if auth_manager.verify_session(token):
                is_authenticated = True
                logger.debug(f"✅ Bearer token认证成功")
            else:
                logger.debug(f"❌ Bearer token认证失败")

        # 2. 检查 Flask session
        if not is_authenticated and 'auth_token' in session:
            logger.debug(f"🔍 检查Flask session")
            if auth_manager.verify_session(session['auth_token']):
                is_authenticated = True
                logger.debug(f"✅ Flask session认证成功")
            else:
                logger.debug(f"❌ Flask session认证失败，清理session")
                # 清理无效的session
                session.clear()

        if is_authenticated:
            logger.debug(f"✅ 认证成功，允许访问 {request.path}")
            return f(*args, **kwargs)

        # 未认证处理
        logger.warning(f"❌ 认证失败，拒绝访问 {request.path}")
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
        logger.info(f"🔐 管理员权限检查 - 路径: {request.path}")

        # 获取token - 优先使用Authorization header，然后是session
        token = None
        token_source = None

        auth_token = request.headers.get('Authorization')
        if auth_token and auth_token.startswith('Bearer '):
            token = auth_token.split(' ')[1]
            token_source = 'header'
            logger.info(f"🔑 使用Authorization header token: {token[:20]}...")
        elif 'auth_token' in session:
            token = session['auth_token']
            token_source = 'session'
            logger.info(f"🔑 使用Flask session token: {token[:20]}...")
        else:
            logger.warning(f"❌ 未找到认证token - 路径: {request.path}")
            logger.warning(f"   - Authorization header: {request.headers.get('Authorization', 'None')}")
            logger.warning(f"   - Session keys: {list(session.keys())}")
            if request.path.startswith('/api/'):
                return jsonify({'error': '需要登录', 'code': 'AUTH_REQUIRED'}), 401
            return redirect(url_for('auth.login'))

        # 验证token
        if not auth_manager.verify_session(token):
            logger.warning(f"❌ token验证失败 - 路径: {request.path}, 来源: {token_source}")
            logger.warning(f"   - Token: {token[:20]}...")
            logger.warning(f"   - 活跃会话数: {len(auth_manager.active_sessions)}")
            if request.path.startswith('/api/'):
                return jsonify({'error': '会话已过期', 'code': 'SESSION_EXPIRED'}), 401
            return redirect(url_for('auth.login'))

        # 检查是否为管理员
        username = auth_manager.get_session_user(token)
        logger.info(f"👤 当前用户: {username}, 管理员: {auth_manager.admin_username}")

        if username != auth_manager.admin_username:
            logger.warning(f"❌ 权限不足 - 用户: {username}, 路径: {request.path}")
            if request.path.startswith('/api/'):
                return jsonify({'error': '需要管理员权限', 'code': 'ADMIN_REQUIRED'}), 403
            # 对于页面请求，重定向到首页并显示错误信息
            return redirect(url_for('main.index') + '?error=permission_denied')

        logger.info(f"✅ 管理员权限验证通过 - 用户: {username}, token来源: {token_source}")
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
