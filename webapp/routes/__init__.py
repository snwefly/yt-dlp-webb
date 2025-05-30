# -*- coding: utf-8 -*-
"""
路由模块初始化
"""

from .main import main_bp
from .auth import auth_bp
from .api import api_bp
from .admin import admin_bp
from .shortcuts import shortcuts_bp

__all__ = ['main_bp', 'auth_bp', 'api_bp', 'admin_bp', 'shortcuts_bp']
