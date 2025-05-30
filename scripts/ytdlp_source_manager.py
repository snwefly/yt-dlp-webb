#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt-dlp 源管理器 - 实现多源获取和版本管理的解耦
"""

import os
import sys
import json
import yaml
import requests
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from abc import ABC, abstractmethod

class YtdlpSourceProvider(ABC):
    """yt-dlp 源提供者抽象基类"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查源是否可用"""
        pass
    
    @abstractmethod
    def get_version_info(self) -> Dict:
        """获取版本信息"""
        pass
    
    @abstractmethod
    def download_source(self, target_dir: str) -> bool:
        """下载源码到目标目录"""
        pass

class GitHubReleaseProvider(YtdlpSourceProvider):
    """GitHub Release 提供者"""
    
    def __init__(self, config: Dict):
        self.repository = config.get('repository', 'yt-dlp/yt-dlp')
        self.version = config.get('version', 'latest')
        self.asset_pattern = config.get('asset_pattern', 'yt-dlp.tar.gz')
        self.fallback_version = config.get('fallback_version', '2024.12.13')
    
    def is_available(self) -> bool:
        """检查 GitHub API 是否可用"""
        try:
            url = f"https://api.github.com/repos/{self.repository}/releases"
            response = requests.get(url, timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_version_info(self) -> Dict:
        """获取版本信息"""
        try:
            if self.version == 'latest':
                url = f"https://api.github.com/repos/{self.repository}/releases/latest"
            else:
                url = f"https://api.github.com/repos/{self.repository}/releases/tags/{self.version}"
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                # 回退到指定版本
                url = f"https://api.github.com/repos/{self.repository}/releases/tags/{self.fallback_version}"
                response = requests.get(url, timeout=10)
                return response.json() if response.status_code == 200 else {}
        except:
            return {}
    
    def download_source(self, target_dir: str) -> bool:
        """下载源码"""
        try:
            version_info = self.get_version_info()
            if not version_info:
                return False
            
            # 查找下载链接
            download_url = None
            for asset in version_info.get('assets', []):
                if self.asset_pattern in asset['name']:
                    download_url = asset['browser_download_url']
                    break
            
            if not download_url:
                # 使用源码包
                download_url = version_info.get('tarball_url')
            
            if not download_url:
                return False
            
            # 下载并解压
            with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
                response = requests.get(download_url, stream=True)
                response.raise_for_status()
                
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                
                tmp_file.flush()
                
                # 解压到目标目录
                with tarfile.open(tmp_file.name, 'r:gz') as tar:
                    tar.extractall(target_dir)
                
                os.unlink(tmp_file.name)
                return True
                
        except Exception as e:
            print(f"GitHub Release 下载失败: {e}")
            return False

class PyPIProvider(YtdlpSourceProvider):
    """PyPI 包提供者"""
    
    def __init__(self, config: Dict):
        self.package = config.get('package', 'yt-dlp')
        self.version = config.get('version', '>=2024.12.13')
        self.index_url = config.get('index_url', 'https://pypi.org/simple/')
    
    def is_available(self) -> bool:
        """检查 PyPI 是否可用"""
        try:
            response = requests.get(f"https://pypi.org/pypi/{self.package}/json", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def get_version_info(self) -> Dict:
        """获取版本信息"""
        try:
            response = requests.get(f"https://pypi.org/pypi/{self.package}/json", timeout=10)
            return response.json() if response.status_code == 200 else {}
        except:
            return {}
    
    def download_source(self, target_dir: str) -> bool:
        """PyPI 通过 requirements.txt 安装，不需要下载源码"""
        return True

class LocalProvider(YtdlpSourceProvider):
    """本地文件提供者"""
    
    def __init__(self, config: Dict):
        self.path = Path(config.get('path', './yt_dlp'))
        self.backup_path = Path(config.get('backup_path', './backup/yt_dlp'))
    
    def is_available(self) -> bool:
        """检查本地文件是否存在"""
        return self.path.exists() or self.backup_path.exists()
    
    def get_version_info(self) -> Dict:
        """获取本地版本信息"""
        version_file = self.path / 'version.py'
        if not version_file.exists() and self.backup_path.exists():
            version_file = self.backup_path / 'version.py'
        
        if version_file.exists():
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 简单解析版本号
                    for line in content.split('\n'):
                        if '__version__' in line:
                            version = line.split('=')[1].strip().strip('"\'')
                            return {'tag_name': version, 'name': f'Local v{version}'}
            except:
                pass
        
        return {'tag_name': 'local', 'name': 'Local Development'}
    
    def download_source(self, target_dir: str) -> bool:
        """复制本地文件"""
        try:
            source_path = self.path if self.path.exists() else self.backup_path
            if not source_path.exists():
                return False
            
            target_path = Path(target_dir) / 'yt_dlp'
            if target_path.exists():
                shutil.rmtree(target_path)
            
            shutil.copytree(source_path, target_path)
            return True
        except Exception as e:
            print(f"本地文件复制失败: {e}")
            return False

class YtdlpSourceManager:
    """yt-dlp 源管理器主类"""
    
    def __init__(self, config_file: str = 'config/ytdlp-source.yml'):
        self.config_file = config_file
        self.config = self._load_config()
        self.providers = self._init_providers()
        self.cache_dir = Path(self.config.get('build_strategy', {}).get('cache', {}).get('directory', './.cache/ytdlp'))
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"配置文件加载失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'ytdlp_source': {'active': 'pypi'},
            'build_strategy': {'priority': ['pypi', 'local']}
        }
    
    def _init_providers(self) -> Dict[str, YtdlpSourceProvider]:
        """初始化提供者"""
        providers = {}
        source_config = self.config.get('ytdlp_source', {})
        
        if source_config.get('github_release', {}).get('enabled', True):
            providers['github_release'] = GitHubReleaseProvider(source_config.get('github_release', {}))
        
        if source_config.get('pypi', {}).get('enabled', True):
            providers['pypi'] = PyPIProvider(source_config.get('pypi', {}))
        
        if source_config.get('local', {}).get('enabled', True):
            providers['local'] = LocalProvider(source_config.get('local', {}))
        
        return providers
    
    def get_best_source(self) -> Tuple[str, YtdlpSourceProvider]:
        """获取最佳可用源"""
        # 检查环境特定配置
        env = os.getenv('ENVIRONMENT', 'production')
        env_config = self.config.get('environments', {}).get(env, {})
        source_override = env_config.get('source_override')
        
        if source_override and source_override in self.providers:
            provider = self.providers[source_override]
            if provider.is_available():
                return source_override, provider
        
        # 按优先级查找可用源
        priority = self.config.get('build_strategy', {}).get('priority', ['pypi', 'local'])
        for source_name in priority:
            if source_name in self.providers:
                provider = self.providers[source_name]
                if provider.is_available():
                    return source_name, provider
        
        # 如果都不可用，返回第一个
        if self.providers:
            first_source = list(self.providers.keys())[0]
            return first_source, self.providers[first_source]
        
        raise RuntimeError("没有可用的 yt-dlp 源")
    
    def prepare_source(self, target_dir: str) -> Dict:
        """准备 yt-dlp 源"""
        source_name, provider = self.get_best_source()
        
        print(f"🔍 使用 yt-dlp 源: {source_name}")
        
        # 获取版本信息
        version_info = provider.get_version_info()
        print(f"📦 版本信息: {version_info.get('name', 'Unknown')}")
        
        # 准备源码
        if source_name == 'pypi':
            # PyPI 不需要下载源码，返回 requirements 信息
            pypi_config = self.config.get('ytdlp_source', {}).get('pypi', {})
            return {
                'source_type': 'pypi',
                'package': pypi_config.get('package', 'yt-dlp'),
                'version': pypi_config.get('version', '>=2024.12.13'),
                'version_info': version_info
            }
        else:
            # 下载源码
            success = provider.download_source(target_dir)
            if not success:
                raise RuntimeError(f"源码下载失败: {source_name}")
            
            return {
                'source_type': 'local',
                'path': target_dir,
                'version_info': version_info
            }

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='yt-dlp 源管理器')
    parser.add_argument('--config', default='config/ytdlp-source.yml', help='配置文件路径')
    parser.add_argument('--target', default='./temp_ytdlp', help='目标目录')
    parser.add_argument('--info-only', action='store_true', help='仅显示信息')
    
    args = parser.parse_args()
    
    try:
        manager = YtdlpSourceManager(args.config)
        
        if args.info_only:
            source_name, provider = manager.get_best_source()
            version_info = provider.get_version_info()
            print(f"最佳源: {source_name}")
            print(f"版本: {version_info.get('name', 'Unknown')}")
        else:
            result = manager.prepare_source(args.target)
            print(f"✅ 源准备完成: {result}")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
