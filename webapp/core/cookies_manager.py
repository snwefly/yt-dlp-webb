"""
YouTube Cookies管理器
负责cookies的导入、验证、备份和管理
"""

import os
import json
import logging
import subprocess
import shutil
import glob
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class CookiesManager:
    """YouTube Cookies管理器"""
    
    def __init__(self):
        # 使用绝对路径，确保在容器中正确工作
        self.cookies_file = os.path.abspath('webapp/config/youtube_cookies.txt')
        self.config_dir = os.path.abspath('webapp/config')
        self.backup_pattern = 'youtube_cookies_backup_*.txt'

        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)
    
    def get_status(self) -> Dict:
        """获取cookies状态"""
        try:
            if not os.path.exists(self.cookies_file):
                return {
                    'exists': False,
                    'status': 'missing',
                    'message': 'YouTube cookies文件不存在'
                }
            
            stat = os.stat(self.cookies_file)
            file_size = stat.st_size
            modified_time = stat.st_mtime
            modified_date = datetime.fromtimestamp(modified_time)
            
            # 分析cookies内容
            important_cookies = self._analyze_cookies()
            
            # 判断状态
            days_since_modified = (datetime.now() - modified_date).days
            
            if days_since_modified > 300:  # 10个月
                status = 'expired'
                message = 'Cookies可能已过期，建议更新'
            elif days_since_modified > 180:  # 6个月
                status = 'warning'
                message = 'Cookies需要关注，建议近期更新'
            elif len(important_cookies) < 3:
                status = 'incomplete'
                message = 'Cookies内容不完整'
            else:
                status = 'good'
                message = 'Cookies状态良好'
            
            return {
                'exists': True,
                'status': status,
                'message': message,
                'file_size': file_size,
                'modified_time': modified_time,
                'modified_date': modified_date.isoformat(),
                'days_since_modified': days_since_modified,
                'important_cookies': important_cookies
            }
            
        except Exception as e:
            logger.error(f"获取cookies状态失败: {e}")
            return {
                'exists': False,
                'status': 'error',
                'message': f'检查状态失败: {str(e)}'
            }
    
    def _analyze_cookies(self) -> List[str]:
        """分析cookies文件，返回找到的重要cookies"""
        important_cookies = ['SID', 'HSID', 'SSID', 'APISID', 'SAPISID', 'LOGIN_INFO', 'VISITOR_INFO1_LIVE']
        found_cookies = []
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split('\t')
                        if len(parts) >= 6 and 'youtube.com' in parts[0]:
                            cookie_name = parts[5]
                            if cookie_name in important_cookies:
                                found_cookies.append(cookie_name)
        except Exception as e:
            logger.error(f"分析cookies失败: {e}")
        
        return found_cookies
    
    def test_cookies(self) -> Dict:
        """测试cookies有效性"""
        try:
            if not os.path.exists(self.cookies_file):
                return {
                    'success': False,
                    'valid': False,
                    'error': 'Cookies文件不存在'
                }

            # 使用yt-dlp测试YouTube视频
            test_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            cmd = [
                'yt-dlp', '--cookies', self.cookies_file,
                '--dump-json', '--no-warnings', '--no-check-certificate',
                test_url
            ]

            logger.info(f"🧪 测试cookies命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)

            logger.info(f"🧪 测试结果返回码: {result.returncode}")
            if result.stderr:
                logger.info(f"🧪 测试错误输出: {result.stderr[:500]}")

            if result.returncode == 0:
                return {
                    'success': True,
                    'valid': True,
                    'message': 'Cookies有效，可以正常下载YouTube视频'
                }
            else:
                # 检查是否是bot检测错误
                if 'Sign in to confirm you\'re not a bot' in result.stderr:
                    return {
                        'success': True,
                        'valid': False,
                        'message': 'Cookies可能已过期，遇到bot检测',
                        'error': 'YouTube要求重新认证，请更新cookies'
                    }
                else:
                    return {
                        'success': True,
                        'valid': False,
                        'message': 'Cookies测试失败',
                        'error': result.stderr[:200] if result.stderr else '未知错误'
                    }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'valid': False,
                'error': '测试超时（45秒）'
            }
        except Exception as e:
            logger.error(f"测试cookies失败: {e}")
            return {
                'success': False,
                'valid': False,
                'error': str(e)
            }
    
    def import_cookies(self, cookies_content: str, format_type: str = 'auto') -> Dict:
        """导入cookies"""
        try:
            if not cookies_content.strip():
                return {
                    'success': False,
                    'error': '请提供cookies内容'
                }
            
            # 备份现有cookies
            backup_file = self._create_backup()
            
            # 检测和转换格式
            final_content, detected_format = self._convert_cookies_format(cookies_content, format_type)
            
            # 验证cookies内容
            validation_result = self._validate_cookies_content(final_content)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'found_cookies': validation_result.get('found_cookies', [])
                }
            
            # 保存新cookies
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            logger.info(f"✅ 新cookies已保存，包含 {len(validation_result['found_cookies'])} 个重要cookies")
            
            # 测试新cookies
            test_result = self.test_cookies()
            
            return {
                'success': True,
                'message': 'Cookies导入成功',
                'detected_format': detected_format,
                'found_cookies': validation_result['found_cookies'],
                'backup_file': backup_file,
                'test_result': test_result
            }
            
        except Exception as e:
            logger.error(f"导入cookies失败: {e}")
            return {
                'success': False,
                'error': f'导入失败: {str(e)}'
            }
    
    def _create_backup(self) -> Optional[str]:
        """创建cookies备份"""
        try:
            if os.path.exists(self.cookies_file):
                timestamp = int(datetime.now().timestamp())
                backup_file = f'youtube_cookies_backup_{timestamp}.txt'
                backup_path = os.path.join(self.config_dir, backup_file)
                shutil.copy(self.cookies_file, backup_path)
                logger.info(f"已备份现有cookies到: {backup_file}")
                return backup_file
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
        return None
    
    def _convert_cookies_format(self, content: str, format_type: str) -> Tuple[str, str]:
        """转换cookies格式 - 智能提取Google/YouTube相关cookies"""
        # 检测格式
        detected_format = 'netscape'
        try:
            json.loads(content)
            detected_format = 'json'
        except:
            if content.startswith('# Netscape HTTP Cookie File'):
                detected_format = 'netscape'
            elif '\t' in content and ('youtube.com' in content or 'google.com' in content):
                detected_format = 'netscape'

        if detected_format == 'json':
            # JSON格式转换为Netscape格式，智能提取Google/YouTube cookies
            cookies_data = json.loads(content)
            netscape_lines = [
                '# Netscape HTTP Cookie File',
                '# This is a generated file! Do not edit.',
                '# Auto-extracted Google/YouTube cookies for yt-dlp',
                ''
            ]

            # 定义需要的域名和重要cookies
            target_domains = ['.google.com', '.youtube.com', 'youtube.com', 'google.com']
            important_cookies = [
                'SID', 'HSID', 'SSID', 'APISID', 'SAPISID',
                'LOGIN_INFO', 'VISITOR_INFO1_LIVE', 'CONSENT',
                '__Secure-1PSID', '__Secure-3PSID', '__Secure-1PAPISID', '__Secure-3PAPISID',
                '__Secure-1PSIDCC', '__Secure-3PSIDCC', '__Secure-1PSIDTS', '__Secure-3PSIDTS',
                'SIDCC', 'NID', 'AEC'
            ]

            extracted_count = 0
            for cookie in cookies_data:
                if isinstance(cookie, dict) and 'domain' in cookie:
                    domain = cookie.get('domain', '')
                    name = cookie.get('name', '')

                    # 检查是否是目标域名
                    is_target_domain = any(target_domain in domain for target_domain in target_domains)

                    # 检查是否是重要cookie或者是目标域名的任何cookie
                    if is_target_domain and (name in important_cookies or domain in ['.google.com', '.youtube.com']):
                        domain_flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'

                        # 处理过期时间
                        expiration = cookie.get('expirationDate', 0)
                        if isinstance(expiration, float):
                            expiration = int(expiration)
                        elif expiration == 0:
                            expiration = 2147483647  # 默认远期时间

                        value = cookie.get('value', '')

                        # 构建Netscape格式行
                        line = f'{domain}\t{domain_flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}'
                        netscape_lines.append(line)
                        extracted_count += 1

                        logger.info(f"✅ 提取cookie: {domain} -> {name}")

            logger.info(f"🍪 从JSON中提取了 {extracted_count} 个Google/YouTube cookies")

            if extracted_count == 0:
                logger.warning("⚠️ 未找到任何Google/YouTube相关cookies")
                # 如果没有找到目标cookies，提取所有cookies作为备用
                for cookie in cookies_data:
                    if isinstance(cookie, dict) and 'domain' in cookie:
                        domain = cookie.get('domain', '')
                        domain_flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                        expiration = int(cookie.get('expirationDate', 2147483647))
                        name = cookie.get('name', '')
                        value = cookie.get('value', '')

                        line = f'{domain}\t{domain_flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}'
                        netscape_lines.append(line)

            return '\n'.join(netscape_lines), detected_format
        else:
            # 已经是Netscape格式
            return content, detected_format
    
    def _validate_cookies_content(self, content: str) -> Dict:
        """验证cookies内容 - 支持Google和YouTube域名"""
        # 扩展重要cookies列表，包含Google的安全cookies
        important_cookies = [
            'SID', 'HSID', 'SSID', 'APISID', 'SAPISID',
            'LOGIN_INFO', 'VISITOR_INFO1_LIVE', 'CONSENT',
            '__Secure-1PSID', '__Secure-3PSID', '__Secure-1PAPISID', '__Secure-3PAPISID',
            '__Secure-1PSIDCC', '__Secure-3PSIDCC', '__Secure-1PSIDTS', '__Secure-3PSIDTS',
            'SIDCC', 'NID', 'AEC'
        ]

        found_cookies = []
        google_cookies = []
        youtube_cookies = []

        for line in content.split('\n'):
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    cookie_name = parts[5]

                    # 检查Google域名cookies
                    if 'google.com' in domain and cookie_name in important_cookies:
                        found_cookies.append(cookie_name)
                        google_cookies.append(cookie_name)

                    # 检查YouTube域名cookies
                    elif 'youtube.com' in domain and cookie_name in important_cookies:
                        found_cookies.append(cookie_name)
                        youtube_cookies.append(cookie_name)

        # 移除重复项
        found_cookies = list(set(found_cookies))

        # 验证逻辑：至少需要一些基础的认证cookies
        basic_auth_cookies = ['SID', '__Secure-1PSID', '__Secure-3PSID']
        has_basic_auth = any(cookie in found_cookies for cookie in basic_auth_cookies)

        if len(found_cookies) < 2 and not has_basic_auth:
            return {
                'valid': False,
                'error': f'cookies内容不完整，只找到 {len(found_cookies)} 个重要cookies',
                'found_cookies': found_cookies,
                'google_cookies': google_cookies,
                'youtube_cookies': youtube_cookies
            }

        return {
            'valid': True,
            'found_cookies': found_cookies,
            'google_cookies': google_cookies,
            'youtube_cookies': youtube_cookies
        }
    
    def list_backups(self) -> List[Dict]:
        """列出备份文件"""
        try:
            backup_pattern = os.path.join(self.config_dir, self.backup_pattern)
            backup_files = glob.glob(backup_pattern)
            
            backups = []
            for file_path in backup_files:
                filename = os.path.basename(file_path)
                timestamp_str = filename.replace('youtube_cookies_backup_', '').replace('.txt', '')
                try:
                    timestamp = int(timestamp_str)
                    created_time = datetime.fromtimestamp(timestamp)
                    file_size = os.path.getsize(file_path)
                    
                    backups.append({
                        'filename': filename,
                        'path': file_path,
                        'created_time': created_time.isoformat(),
                        'created_time_str': created_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'file_size': file_size
                    })
                except ValueError:
                    continue
            
            # 按时间倒序排列
            backups.sort(key=lambda x: x['created_time'], reverse=True)
            return backups
            
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []
    
    def restore_backup(self, backup_filename: str) -> Dict:
        """恢复备份"""
        try:
            backup_path = os.path.join(self.config_dir, backup_filename)
            
            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'error': '备份文件不存在'
                }
            
            # 创建当前cookies的备份
            current_backup = self._create_backup()
            
            # 恢复备份
            shutil.copy(backup_path, self.cookies_file)
            
            logger.info(f"✅ 已恢复cookies备份: {backup_filename}")
            
            return {
                'success': True,
                'message': f'已恢复备份: {backup_filename}',
                'current_backup': current_backup
            }
            
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# 全局实例
_cookies_manager = CookiesManager()

def get_cookies_manager():
    """获取cookies管理器实例"""
    return _cookies_manager
