# -*- coding: utf-8 -*-
"""
下载管理器 - 简化版本
"""

import uuid
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DownloadManager:
    """下载管理器"""
    
    def __init__(self):
        self.downloads = {}
        self.lock = threading.Lock()
    
    def create_download(self, url, options=None):
        """创建下载任务"""
        download_id = str(uuid.uuid4())
        
        download_info = {
            'id': download_id,
            'url': url,
            'status': 'pending',
            'progress': 0,
            'created_at': datetime.now(),
            'options': options or {}
        }
        
        with self.lock:
            self.downloads[download_id] = download_info
        
        return download_id
    
    def get_download(self, download_id):
        """获取下载信息"""
        with self.lock:
            return self.downloads.get(download_id)
    
    def get_all_downloads(self):
        """获取所有下载"""
        with self.lock:
            return list(self.downloads.values())
    
    def update_download(self, download_id, **kwargs):
        """更新下载信息"""
        with self.lock:
            if download_id in self.downloads:
                self.downloads[download_id].update(kwargs)
                return True
        return False

# 全局实例
_download_manager = DownloadManager()

def get_download_manager():
    """获取下载管理器实例"""
    return _download_manager
