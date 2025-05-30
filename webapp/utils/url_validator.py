# -*- coding: utf-8 -*-
"""
URL 验证工具
"""

import re
from urllib.parse import urlparse

def validate_url(url):
    """
    验证URL的安全性和有效性
    
    Args:
        url (str): 要验证的URL
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL不能为空"
    
    url = url.strip()
    
    # 基本URL格式验证
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "无效的URL格式"
    except Exception:
        return False, "URL解析失败"
    
    # 协议验证
    if parsed.scheme.lower() not in ['http', 'https']:
        return False, "只支持HTTP和HTTPS协议"
    
    # 域名黑名单检查
    blocked_domains = [
        'localhost',
        '127.0.0.1',
        '0.0.0.0',
        '::1'
    ]
    
    if parsed.netloc.lower() in blocked_domains:
        return False, "不允许访问本地地址"
    
    # 内网IP检查
    if _is_private_ip(parsed.netloc):
        return False, "不允许访问内网地址"
    
    # URL长度检查
    if len(url) > 2048:
        return False, "URL过长"
    
    return True, ""

def _is_private_ip(hostname):
    """检查是否为内网IP"""
    # 简单的内网IP检查
    private_patterns = [
        r'^10\.',
        r'^172\.(1[6-9]|2[0-9]|3[01])\.',
        r'^192\.168\.',
        r'^169\.254\.',
    ]
    
    for pattern in private_patterns:
        if re.match(pattern, hostname):
            return True
    
    return False
