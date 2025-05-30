#!/usr/bin/env python3
"""
文件自动清理系统
负责清理下载文件夹中的过期文件
"""

import os
import time
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path

class FileCleanupManager:
    """文件清理管理器"""

    def __init__(self, download_folder, config=None):
        self.download_folder = Path(download_folder)
        self.config = config or {}
        self.cleanup_thread = None
        self.running = False

        # 默认配置
        self.default_config = {
            'auto_cleanup_enabled': True,
            'cleanup_interval_hours': 1,  # 每小时检查一次
            'file_retention_hours': 24,   # 文件保留24小时
            'max_storage_mb': 1024,       # 最大存储1GB
            'cleanup_on_download': True,  # 下载完成后立即清理
            'keep_recent_files': 10,      # 至少保留最近10个文件
            'temp_file_retention_minutes': 30,  # 临时文件保留30分钟
        }

        # 合并配置
        self.settings = {**self.default_config, **self.config}

        # 设置日志
        self.logger = logging.getLogger('FileCleanup')

    def start_auto_cleanup(self):
        """启动自动清理线程"""
        if not self.settings['auto_cleanup_enabled']:
            self.logger.info("自动清理已禁用")
            return

        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.logger.warning("清理线程已在运行")
            return

        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        self.logger.info("自动清理线程已启动")

    def stop_auto_cleanup(self):
        """停止自动清理"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        self.logger.info("自动清理线程已停止")

    def _cleanup_worker(self):
        """清理工作线程"""
        interval = self.settings['cleanup_interval_hours'] * 3600

        while self.running:
            try:
                self.cleanup_files()
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"清理过程中出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再重试

    def cleanup_files(self):
        """执行文件清理"""
        if not self.download_folder.exists():
            return

        self.logger.info("开始清理文件...")

        # 1. 清理过期文件
        expired_count = self._cleanup_expired_files()

        # 2. 清理临时文件
        temp_count = self._cleanup_temp_files()

        # 3. 检查存储空间限制
        storage_count = self._cleanup_by_storage_limit()

        # 4. 清理空目录
        self._cleanup_empty_dirs()

        total_cleaned = expired_count + temp_count + storage_count
        if total_cleaned > 0:
            self.logger.info(f"清理完成: 删除了 {total_cleaned} 个文件")

        return total_cleaned

    def _cleanup_expired_files(self):
        """清理过期文件"""
        retention_hours = self.settings['file_retention_hours']
        cutoff_time = datetime.now() - timedelta(hours=retention_hours)

        cleaned_count = 0
        files = list(self.download_folder.glob('*'))

        # 按修改时间排序，保留最新的文件
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        keep_recent = self.settings['keep_recent_files']

        for i, file_path in enumerate(files):
            if file_path.is_file():
                # 保留最近的文件
                if i < keep_recent:
                    continue

                # 检查文件是否过期
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"删除过期文件: {file_path.name}")
                    except Exception as e:
                        self.logger.error(f"删除文件失败 {file_path}: {e}")

        return cleaned_count

    def _cleanup_temp_files(self):
        """清理临时文件"""
        retention_minutes = self.settings['temp_file_retention_minutes']
        cutoff_time = datetime.now() - timedelta(minutes=retention_minutes)

        cleaned_count = 0

        # 查找临时文件（以temp_开头的文件）
        for file_path in self.download_folder.glob('temp_*'):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        self.logger.debug(f"删除临时文件: {file_path.name}")
                    except Exception as e:
                        self.logger.error(f"删除临时文件失败 {file_path}: {e}")

        return cleaned_count

    def _cleanup_by_storage_limit(self):
        """根据存储限制清理文件"""
        max_storage_bytes = self.settings['max_storage_mb'] * 1024 * 1024

        # 计算当前存储使用量
        total_size = sum(f.stat().st_size for f in self.download_folder.glob('*') if f.is_file())

        if total_size <= max_storage_bytes:
            return 0

        self.logger.info(f"存储超限: {total_size / 1024 / 1024:.1f}MB > {max_storage_bytes / 1024 / 1024:.1f}MB")

        # 按修改时间排序，删除最旧的文件
        files = [(f, f.stat().st_mtime, f.stat().st_size)
                for f in self.download_folder.glob('*') if f.is_file()]
        files.sort(key=lambda x: x[1])  # 按时间排序

        cleaned_count = 0
        keep_recent = self.settings['keep_recent_files']

        for i, (file_path, mtime, size) in enumerate(files):
            # 保留最近的文件
            if len(files) - i <= keep_recent:
                break

            try:
                file_path.unlink()
                total_size -= size
                cleaned_count += 1
                self.logger.debug(f"删除文件以释放空间: {file_path.name}")

                if total_size <= max_storage_bytes:
                    break
            except Exception as e:
                self.logger.error(f"删除文件失败 {file_path}: {e}")

        return cleaned_count

    def _cleanup_empty_dirs(self):
        """清理空目录"""
        try:
            for dir_path in self.download_folder.iterdir():
                if dir_path.is_dir() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    self.logger.debug(f"删除空目录: {dir_path.name}")
        except Exception as e:
            self.logger.error(f"清理空目录失败: {e}")

    def cleanup_on_download_complete(self, filename):
        """下载完成后的清理"""
        if not self.settings['cleanup_on_download']:
            return

        # 立即清理临时文件
        self._cleanup_temp_files()

        # 如果存储空间紧张，立即清理
        max_storage_bytes = self.settings['max_storage_mb'] * 1024 * 1024
        total_size = sum(f.stat().st_size for f in self.download_folder.glob('*') if f.is_file())

        if total_size > max_storage_bytes * 0.8:  # 超过80%时清理
            self.logger.info("存储空间紧张，执行立即清理")
            self.cleanup_files()

    def get_storage_info(self):
        """获取存储信息"""
        if not self.download_folder.exists():
            return {
                'total_files': 0,
                'total_size_mb': 0,
                'max_storage_mb': self.settings['max_storage_mb'],
                'usage_percent': 0
            }

        files = list(self.download_folder.glob('*'))
        file_count = len([f for f in files if f.is_file()])
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        total_size_mb = total_size / 1024 / 1024
        max_storage_mb = self.settings['max_storage_mb']
        usage_percent = (total_size_mb / max_storage_mb) * 100 if max_storage_mb > 0 else 0

        return {
            'total_files': file_count,
            'total_size_mb': round(total_size_mb, 2),
            'max_storage_mb': max_storage_mb,
            'usage_percent': round(usage_percent, 1)
        }

    def get_config(self):
        """获取当前配置"""
        return self.settings.copy()

    def update_config(self, new_config):
        """更新配置"""
        self.settings.update(new_config)
        self.logger.info("清理配置已更新")


# 全局清理管理器实例
cleanup_manager = None

def initialize_cleanup_manager(download_folder, config=None):
    """初始化清理管理器"""
    global cleanup_manager
    cleanup_manager = FileCleanupManager(download_folder, config)
    cleanup_manager.start_auto_cleanup()
    return cleanup_manager

def get_cleanup_manager():
    """获取清理管理器实例"""
    return cleanup_manager
