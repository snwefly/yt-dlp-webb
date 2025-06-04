"""
数据库模型定义 - 使用Flask-Login
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """用户模型 - 使用Flask-Login的UserMixin"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """检查密码"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class TelegramConfig(db.Model):
    """Telegram配置模型"""
    __tablename__ = 'telegram_config'

    id = db.Column(db.Integer, primary_key=True)
    bot_token = db.Column(db.String(255), nullable=True)
    chat_id = db.Column(db.String(100), nullable=True)
    api_id = db.Column(db.String(20), nullable=True)  # Telegram API ID
    api_hash = db.Column(db.String(50), nullable=True)  # Telegram API Hash
    webhook_enabled = db.Column(db.Boolean, default=False)
    webhook_secret = db.Column(db.String(255), nullable=True)
    push_mode = db.Column(db.String(20), default='file')  # file, notification, both
    auto_download = db.Column(db.Boolean, default=True)
    file_size_limit_mb = db.Column(db.Integer, default=50)  # Telegram文件大小限制
    enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 高级设置（JSON格式存储）
    advanced_settings = db.Column(db.Text, nullable=True)

    def get_advanced_settings(self):
        """获取高级设置"""
        if self.advanced_settings:
            try:
                return json.loads(self.advanced_settings)
            except:
                return {}
        return {}

    def set_advanced_settings(self, settings_dict):
        """设置高级设置"""
        self.advanced_settings = json.dumps(settings_dict)

    @classmethod
    def get_config(cls):
        """获取当前配置（单例模式）"""
        config = cls.query.first()
        if not config:
            # 创建默认配置
            config = cls()
            db.session.add(config)
            db.session.commit()
        return config

    def is_configured(self):
        """检查是否已配置"""
        return bool(self.bot_token and self.chat_id)

    def __repr__(self):
        return f'<TelegramConfig enabled={self.enabled}>'
