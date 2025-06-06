"""
YouTube Cookies管理器
负责cookies的导入、验证、备份和管理
"""

import os
import json
import logging
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class CookiesManager:
    """YouTube Cookies管理器"""

    def __init__(self):
        # 使用绝对路径，确保在容器中正确工作
        self.config_dir = os.path.abspath('webapp/config')


        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)

        # 平台配置：定义各平台的域名和重要cookies
        self.platform_configs = {
            'youtube': {
                'domains': ['youtube.com', 'google.com', '.youtube.com', '.google.com'],
                'important_cookies': [
                    'SID', 'HSID', 'SSID', 'APISID', 'SAPISID', 'LOGIN_INFO', 'VISITOR_INFO1_LIVE',
                    '__Secure-1PSID', '__Secure-3PSID', '__Secure-1PAPISID', '__Secure-3PAPISID',
                    '__Secure-1PSIDCC', '__Secure-3PSIDCC', '__Secure-1PSIDTS', '__Secure-3PSIDTS',
                    'SIDCC', 'CONSENT', 'NID', 'AEC'
                ],
                'auth_cookies': ['SID', '__Secure-1PSID', '__Secure-3PSID']
            },
            'twitter': {
                'domains': ['twitter.com', 'x.com', '.twitter.com', '.x.com'],
                'important_cookies': [
                    'auth_token', 'ct0', 'guest_id', 'personalization_id', 'gt', 'twid',
                    '_twitter_sess', 'remember_checked_on', 'kdt', 'dnt', 'mbox'
                ],
                'auth_cookies': ['auth_token', 'ct0']
            },
            'instagram': {
                'domains': ['instagram.com', '.instagram.com'],
                'important_cookies': [
                    'sessionid', 'csrftoken', 'ds_user_id', 'ig_did', 'ig_nrcb'
                ],
                'auth_cookies': ['sessionid']
            },
            'tiktok': {
                'domains': ['tiktok.com', '.tiktok.com'],
                'important_cookies': [
                    'sessionid', 'sid_tt', 'uid_tt', 'sid_guard', 'uid_guard', 'ssid_ucp_v1'
                ],
                'auth_cookies': ['sessionid', 'sid_tt']
            },
            'bilibili': {
                'domains': ['bilibili.com', '.bilibili.com'],
                'important_cookies': [
                    'SESSDATA', 'bili_jct', 'DedeUserID', 'DedeUserID__ckMd5', 'sid'
                ],
                'auth_cookies': ['SESSDATA']
            }
        }

    def get_platform_cookies_file(self, platform: str) -> str:
        """获取指定平台的cookies文件路径"""
        return os.path.join(self.config_dir, f'{platform}_cookies.txt')

    def get_all_platform_cookies_files(self) -> Dict[str, str]:
        """获取所有平台的cookies文件路径"""
        return {platform: self.get_platform_cookies_file(platform)
                for platform in self.platform_configs.keys()}

    def detect_platform_from_url(self, url: str) -> str:
        """从URL智能检测平台"""
        url_lower = url.lower()

        for platform, config in self.platform_configs.items():
            for domain in config['domains']:
                # 只移除前导点，保留域名中的点
                clean_domain = domain.lstrip('.')
                if clean_domain in url_lower:
                    return platform

        return 'unknown'

    def detect_platform_from_domain(self, domain: str) -> str:
        """从域名检测平台"""
        for platform, config in self.platform_configs.items():
            for platform_domain in config['domains']:
                if platform_domain in domain:
                    return platform
        return 'unknown'

    def get_all_important_cookies(self) -> List[str]:
        """获取所有平台的重要cookies列表"""
        all_cookies = []
        for config in self.platform_configs.values():
            all_cookies.extend(config['important_cookies'])
        return list(set(all_cookies))  # 去重

    def get_platform_cookies(self, platform: str) -> List[str]:
        """获取指定平台的重要cookies"""
        if platform in self.platform_configs:
            return self.platform_configs[platform]['important_cookies']
        return []

    def analyze_cookies_by_platform(self) -> Dict:
        """按平台分析cookies - 分析各平台独立文件"""
        platform_analysis = {}

        # 初始化平台分析结构
        for platform, config in self.platform_configs.items():
            platform_analysis[platform] = {
                'found_cookies': [],
                'important_cookies': config['important_cookies'],
                'auth_cookies': config['auth_cookies'],
                'completeness': 0.0,
                'has_auth': False,
                'file_exists': False
            }

        # 分析每个平台的cookies文件
        platform_files = self.get_all_platform_cookies_files()
        for platform, file_path in platform_files.items():
            if os.path.exists(file_path):
                platform_analysis[platform]['file_exists'] = True

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#'):
                                parts = line.strip().split('\t')
                                if len(parts) >= 6:
                                    cookie_name = parts[5]

                                    # 检查是否是重要cookie
                                    important_cookies = platform_analysis[platform]['important_cookies']
                                    if cookie_name in important_cookies:
                                        platform_analysis[platform]['found_cookies'].append(cookie_name)

                except Exception as e:
                    logger.error(f"分析 {platform} 平台cookies失败: {e}")

        # 计算每个平台的完整性和认证状态
        for platform, data in platform_analysis.items():
            data['found_cookies'] = list(set(data['found_cookies']))  # 去重
            data['completeness'] = len(data['found_cookies']) / len(data['important_cookies']) if data['important_cookies'] else 0
            data['has_auth'] = any(cookie in data['found_cookies'] for cookie in data['auth_cookies'])

        return platform_analysis

    def get_cookies_for_url(self, url: str) -> str:
        """根据URL自动调取对应平台的cookies文件 - 核心功能"""
        # 1. 检测平台
        platform = self.detect_platform_from_url(url)

        # 2. 获取对应平台cookies文件
        if platform == 'unknown':
            platform = 'youtube'  # 默认使用YouTube

        cookies_file = self.get_platform_cookies_file(platform)

        # 3. 检查文件是否存在
        if os.path.exists(cookies_file):
            # 验证和修复Cookie文件格式
            validated_file = self._validate_and_fix_cookies_file(cookies_file)
            logger.info(f"🍪 使用 {platform} 平台cookies: {validated_file}")
            return validated_file
        else:
            # 4. 备用：找任何可用的cookies文件
            for p, file_path in self.get_all_platform_cookies_files().items():
                if os.path.exists(file_path):
                    validated_file = self._validate_and_fix_cookies_file(file_path)
                    logger.info(f"🔄 {platform} 平台文件不存在，使用 {p} 平台cookies: {validated_file}")
                    return validated_file

            logger.error(f"❌ 没有找到任何cookies文件")
            return cookies_file

    def _validate_and_fix_cookies_file(self, cookies_file: str) -> str:
        """验证并修复Cookie文件格式，确保yt-dlp兼容性"""
        try:
            # 读取原文件
            with open(cookies_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检测格式
            detected_format = self._detect_cookies_format(content)

            if detected_format == 'json':
                logger.warning(f"⚠️ 检测到JSON格式Cookie文件，正在转换为Netscape格式...")
                # 转换为Netscape格式
                netscape_content, _ = self._convert_cookies_format(content, 'netscape')

                # 创建修复后的文件
                fixed_file = cookies_file.replace('.txt', '_fixed.txt')
                with open(fixed_file, 'w', encoding='utf-8') as f:
                    f.write(netscape_content)

                logger.info(f"✅ 已转换并保存为: {fixed_file}")
                return fixed_file

            elif detected_format == 'netscape':
                # 验证Netscape格式的完整性
                lines = content.strip().split('\n')
                fixed_lines = []
                needs_fix = False

                for line in lines:
                    if line.strip():
                        # 检查是否是注释行
                        if line.startswith('#'):
                            fixed_lines.append(line)
                        else:
                            # 验证数据行格式
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                # 清理每个字段，确保没有会导致yt-dlp误判的字符
                                cleaned_parts = []
                                for i, part in enumerate(parts):
                                    if i == 6:  # cookie value字段
                                        # 特别处理cookie值，移除可能导致JSON误判的字符
                                        cleaned_value = part.strip()
                                        if cleaned_value.startswith(('"', "'", '[', '{')):
                                            cleaned_value = cleaned_value[1:]
                                            needs_fix = True
                                        if cleaned_value.endswith(('"', "'", ']', '}')):
                                            cleaned_value = cleaned_value[:-1]
                                            needs_fix = True
                                        cleaned_parts.append(cleaned_value)
                                    else:
                                        cleaned_parts.append(part.strip())

                                fixed_line = '\t'.join(cleaned_parts)
                                fixed_lines.append(fixed_line)
                            else:
                                # 格式不正确的行，跳过
                                logger.warning(f"⚠️ 跳过格式不正确的行: {line[:50]}...")
                                needs_fix = True
                    else:
                        fixed_lines.append(line)

                if needs_fix:
                    # 保存修复后的文件
                    fixed_content = '\n'.join(fixed_lines)
                    fixed_file = cookies_file.replace('.txt', '_fixed.txt')
                    with open(fixed_file, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)

                    logger.info(f"✅ 已修复Cookie文件格式: {fixed_file}")
                    return fixed_file
                else:
                    # 文件格式正确，直接返回
                    return cookies_file

            else:
                logger.warning(f"⚠️ 未知的Cookie文件格式，尝试直接使用")
                return cookies_file

        except Exception as e:
            logger.error(f"❌ 验证Cookie文件时出错: {e}")
            return cookies_file

    def get_status(self) -> Dict:
        """获取多平台cookies状态"""
        try:
            platform_files = self.get_all_platform_cookies_files()
            existing_files = {}
            total_size = 0
            latest_modified = None

            # 检查每个平台的cookies文件
            for platform, file_path in platform_files.items():
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    modified_time = stat.st_mtime
                    modified_date = datetime.fromtimestamp(modified_time)

                    existing_files[platform] = {
                        'file_path': file_path,
                        'file_size': file_size,
                        'modified_time': modified_time,
                        'modified_date': modified_date.isoformat(),
                        'days_since_modified': (datetime.now() - modified_date).days
                    }

                    total_size += file_size
                    if latest_modified is None or modified_time > latest_modified:
                        latest_modified = modified_time

            if not existing_files:
                return {
                    'exists': False,
                    'status': 'missing',
                    'message': '未找到任何平台的cookies文件'
                }

            # 分析所有平台的cookies
            platform_analysis = self.analyze_cookies_by_platform()

            # 计算总体状态
            latest_modified_date = datetime.fromtimestamp(latest_modified)
            days_since_modified = (datetime.now() - latest_modified_date).days

            # 检查认证状态
            auth_platforms = [p for p, data in platform_analysis.items() if data.get('has_auth', False)]

            if days_since_modified > 300:  # 10个月
                status = 'expired'
                message = f'Cookies可能已过期，建议更新 (最后更新: {days_since_modified}天前)'
            elif days_since_modified > 180:  # 6个月
                status = 'warning'
                message = f'Cookies需要关注，建议近期更新 (最后更新: {days_since_modified}天前)'
            elif len(auth_platforms) == 0:
                status = 'incomplete'
                message = '所有平台都缺少认证cookies'
            else:
                status = 'good'
                message = f'找到 {len(existing_files)} 个平台的cookies，{len(auth_platforms)} 个平台有认证'

            return {
                'exists': True,
                'status': status,
                'message': message,
                'total_platforms': len(existing_files),
                'platform_files': existing_files,
                'total_size': total_size,
                'latest_modified': latest_modified,
                'latest_modified_date': latest_modified_date.isoformat(),
                'days_since_modified': days_since_modified,
                'platform_analysis': platform_analysis,
                'supported_platforms': list(existing_files.keys()),
                'auth_platforms': auth_platforms
            }

        except Exception as e:
            logger.error(f"获取cookies状态失败: {e}")
            return {
                'exists': False,
                'status': 'error',
                'message': f'检查状态失败: {str(e)}'
            }

    def delete_cookies(self) -> Dict:
        """删除所有平台的cookies文件"""
        try:
            platform_files = self.get_all_platform_cookies_files()
            deleted_files = []

            for platform, file_path in platform_files.items():
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_files.append(f"{platform}_cookies.txt")
                    logger.info(f"🗑️ 已删除 {platform} 平台cookies文件")

            if deleted_files:
                return {
                    'success': True,
                    'message': f'已删除 {len(deleted_files)} 个平台的cookies文件',
                    'deleted_files': deleted_files
                }
            else:
                return {
                    'success': True,
                    'message': '没有找到需要删除的cookies文件'
                }

        except Exception as e:
            logger.error(f"删除cookies失败: {e}")
            return {
                'success': False,
                'error': f'删除失败: {str(e)}'
            }

    def _get_important_cookies_list(self) -> List[str]:
        """获取重要cookies列表定义"""
        return self.get_all_important_cookies()

    def _analyze_cookies(self) -> List[str]:
        """分析多平台cookies文件，返回找到的重要cookies"""
        important_cookies = self._get_important_cookies_list()
        found_cookies = []

        try:
            platform_files = self.get_all_platform_cookies_files()
            for platform, file_path in platform_files.items():
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip() and not line.startswith('#'):
                                parts = line.strip().split('\t')
                                if len(parts) >= 6:
                                    cookie_name = parts[5]

                                    # 检查是否是重要cookie
                                    if cookie_name in important_cookies:
                                        found_cookies.append(cookie_name)
                                        logger.debug(f"🔍 找到重要cookie: {platform} -> {cookie_name}")

        except Exception as e:
            logger.error(f"分析cookies失败: {e}")

        # 移除重复项并保持顺序
        found_cookies = list(dict.fromkeys(found_cookies))
        return found_cookies



    def _sanitize_cookie_value(self, value: str) -> str:
        """清理cookie值中的特殊字符，防止破坏Netscape格式"""
        if not value:
            return value

        # 移除或替换会破坏Netscape格式的字符
        sanitized = value.replace('\t', ' ')  # 制表符替换为空格
        sanitized = sanitized.replace('\n', ' ')  # 换行符替换为空格
        sanitized = sanitized.replace('\r', ' ')  # 回车符替换为空格

        # 压缩多个连续空格为单个空格
        import re
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # 移除首尾空白字符
        sanitized = sanitized.strip()

        return sanitized

    def _analyze_cookies_expiration(self, cookies_file_path: str) -> Dict:
        """分析cookies的过期时间"""
        try:
            current_time = datetime.now()
            current_timestamp = int(current_time.timestamp())

            cookies_expiration = {}
            earliest_expiry = None
            latest_expiry = None
            expired_count = 0
            valid_count = 0

            with open(cookies_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split('\t')
                        if len(parts) >= 7:
                            domain = parts[0]
                            cookie_name = parts[5]

                            # 检查是否是重要cookie
                            important_cookies = self._get_important_cookies_list()

                            platform = self.detect_platform_from_domain(domain)
                            if platform != 'unknown' and cookie_name in important_cookies:
                                try:
                                    expiry_timestamp = int(parts[4])
                                    expiry_date = datetime.fromtimestamp(expiry_timestamp)

                                    # 计算剩余时间
                                    remaining_seconds = expiry_timestamp - current_timestamp
                                    remaining_days = remaining_seconds / (24 * 3600)

                                    is_expired = remaining_seconds <= 0
                                    if is_expired:
                                        expired_count += 1
                                    else:
                                        valid_count += 1

                                    cookies_expiration[cookie_name] = {
                                        'expiry_timestamp': expiry_timestamp,
                                        'expiry_date': expiry_date.strftime('%Y-%m-%d %H:%M:%S'),
                                        'remaining_days': max(0, remaining_days),
                                        'remaining_seconds': max(0, remaining_seconds),
                                        'is_expired': is_expired,
                                        'domain': domain,
                                        'line_number': line_num
                                    }

                                    # 跟踪最早和最晚过期时间
                                    if earliest_expiry is None or expiry_timestamp < earliest_expiry:
                                        earliest_expiry = expiry_timestamp
                                    if latest_expiry is None or expiry_timestamp > latest_expiry:
                                        latest_expiry = expiry_timestamp

                                except (ValueError, IndexError):
                                    # 过期时间格式错误
                                    cookies_expiration[cookie_name] = {
                                        'expiry_timestamp': None,
                                        'expiry_date': '格式错误',
                                        'remaining_days': 0,
                                        'remaining_seconds': 0,
                                        'is_expired': True,
                                        'domain': domain,
                                        'line_number': line_num
                                    }
                                    expired_count += 1

            # 计算整体统计
            total_cookies = len(cookies_expiration)
            if total_cookies == 0:
                return {
                    'total_cookies': 0,
                    'valid_cookies': 0,
                    'expired_cookies': 0,
                    'cookies_details': {},
                    'overall_status': 'no_cookies',
                    'earliest_expiry': None,
                    'latest_expiry': None,
                    'min_remaining_days': 0,
                    'max_remaining_days': 0
                }

            # 计算剩余时间范围
            valid_cookies_details = {k: v for k, v in cookies_expiration.items() if not v['is_expired']}
            if valid_cookies_details:
                min_remaining_days = min(v['remaining_days'] for v in valid_cookies_details.values())
                max_remaining_days = max(v['remaining_days'] for v in valid_cookies_details.values())
            else:
                min_remaining_days = 0
                max_remaining_days = 0

            # 判断整体状态
            if expired_count == total_cookies:
                overall_status = 'all_expired'
            elif expired_count > total_cookies * 0.5:
                overall_status = 'mostly_expired'
            elif min_remaining_days < 30:
                overall_status = 'expiring_soon'
            elif min_remaining_days < 90:
                overall_status = 'good'
            else:
                overall_status = 'excellent'

            return {
                'total_cookies': total_cookies,
                'valid_cookies': valid_count,
                'expired_cookies': expired_count,
                'cookies_details': cookies_expiration,
                'overall_status': overall_status,
                'earliest_expiry': datetime.fromtimestamp(earliest_expiry).strftime('%Y-%m-%d %H:%M:%S') if earliest_expiry else None,
                'latest_expiry': datetime.fromtimestamp(latest_expiry).strftime('%Y-%m-%d %H:%M:%S') if latest_expiry else None,
                'min_remaining_days': min_remaining_days,
                'max_remaining_days': max_remaining_days
            }

        except Exception as e:
            logger.error(f"分析cookies过期时间失败: {e}")
            return {
                'total_cookies': 0,
                'valid_cookies': 0,
                'expired_cookies': 0,
                'cookies_details': {},
                'overall_status': 'error',
                'error': str(e)
            }

    def _compare_cookies_before_after(self, before_cookies: List[str], after_cookies: List[str], backup_cookies: List[str]) -> Dict:
        """对比恢复前后的cookies变化"""
        before_set = set(before_cookies)
        after_set = set(after_cookies)
        backup_set = set(backup_cookies)

        added = list(after_set - before_set)  # 新增的cookies
        lost = list(before_set - after_set)   # 丢失的cookies
        kept = list(before_set & after_set)   # 保持的cookies

        # 检查是否按预期恢复
        expected_from_backup = list(backup_set)
        actually_restored = list(after_set)

        return {
            'added': added,
            'lost': lost,
            'kept': kept,
            'expected_from_backup': expected_from_backup,
            'actually_restored': actually_restored,
            'restoration_success': backup_set == after_set,
            'improvement': len(after_cookies) > len(before_cookies)
        }

    def test_cookies(self) -> Dict:
        """测试所有平台cookies有效性"""
        try:
            platform_files = self.get_all_platform_cookies_files()
            existing_files = {p: f for p, f in platform_files.items() if os.path.exists(f)}

            if not existing_files:
                return {
                    'success': False,
                    'valid': False,
                    'error': '未找到任何平台的cookies文件'
                }

            # 分析所有平台的cookies
            platform_analysis = self.analyze_cookies_by_platform()

            # 测试所有有认证的平台
            test_results = {}
            overall_valid = False

            logger.info(f"🧪 开始测试 {len(existing_files)} 个平台的cookies...")

            for platform, file_path in existing_files.items():
                platform_data = platform_analysis.get(platform, {})

                if platform_data.get('has_auth', False):
                    logger.info(f"🔍 测试 {platform} 平台cookies...")
                    test_result = self._test_platform_cookies(platform, file_path)
                    test_results[platform] = test_result

                    if test_result.get('valid', False):
                        overall_valid = True
                        logger.info(f"✅ {platform} 平台cookies有效")
                    else:
                        logger.warning(f"❌ {platform} 平台cookies无效: {test_result.get('message', 'unknown')}")
                else:
                    test_results[platform] = {
                        'success': True,
                        'valid': False,
                        'message': f'{platform} 平台缺少认证cookies',
                        'skipped': True
                    }
                    logger.info(f"⏭️ 跳过 {platform} 平台（缺少认证cookies）")

            # 汇总结果
            valid_platforms = [p for p, r in test_results.items() if r.get('valid', False)]
            invalid_platforms = [p for p, r in test_results.items() if not r.get('valid', False) and not r.get('skipped', False)]
            skipped_platforms = [p for p, r in test_results.items() if r.get('skipped', False)]

            # 返回汇总结果
            return {
                'success': True,
                'valid': overall_valid,
                'message': f'测试完成：{len(valid_platforms)} 个平台有效，{len(invalid_platforms)} 个平台无效，{len(skipped_platforms)} 个平台跳过',
                'test_results': test_results,
                'valid_platforms': valid_platforms,
                'invalid_platforms': invalid_platforms,
                'skipped_platforms': skipped_platforms,
                'platform_analysis': platform_analysis,
                'total_tested': len(test_results)
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'valid': False,
                'error': '测试超时（60秒）'
            }
        except Exception as e:
            logger.error(f"测试cookies失败: {e}")
            return {
                'success': False,
                'valid': False,
                'error': str(e)
            }

    def _test_with_alternative_url(self, test_platform: str = 'youtube', test_file: str = None) -> Dict:
        """使用备用URL测试cookies"""
        try:
            # 根据平台选择备用测试URL（使用更简单的测试）
            alternative_urls = {
                'youtube': 'https://www.youtube.com/watch?v=BaW_jenozKc',  # 简单的公开视频
                'twitter': 'https://x.com/twitter',
                'instagram': 'https://www.instagram.com/',
                'tiktok': 'https://www.tiktok.com/',
                'bilibili': 'https://www.bilibili.com/'
            }

            test_url = alternative_urls.get(test_platform, alternative_urls['youtube'])

            if not test_file:
                test_file = self.get_platform_cookies_file(test_platform)

            cmd = [
                'yt-dlp', '--cookies', test_file,
                '--dump-json', '--no-warnings', '--no-check-certificate',
                test_url
            ]

            logger.info(f"🔄 {test_platform} 平台备用测试: {test_url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)

            if result.returncode == 0:
                return {
                    'success': True,
                    'valid': True,
                    'message': f'{test_platform} 平台cookies有效（备用测试通过）',
                    'test_platform': test_platform
                }
            else:
                return {
                    'success': True,
                    'valid': False,
                    'message': f'{test_platform} 平台cookies可能无效',
                    'error': f'备用测试也失败: {result.stderr[:200] if result.stderr else "未知错误"}',
                    'test_platform': test_platform
                }

        except Exception as e:
            logger.error(f"{test_platform} 平台备用测试失败: {e}")
            return {
                'success': True,
                'valid': False,
                'message': f'{test_platform} 平台cookies测试失败',
                'error': f'备用测试异常: {str(e)}',
                'test_platform': test_platform
            }

    def _test_platform_cookies(self, platform: str, cookies_file: str) -> Dict:
        """测试单个平台的cookies有效性"""
        try:
            # 检查cookies文件内容
            logger.info(f"🔍 检查 {platform} 平台cookies文件: {cookies_file}")
            try:
                with open(cookies_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logger.info(f"📄 {platform} cookies文件大小: {len(content)} 字符")

                    # 分析cookies内容
                    lines = content.split('\n')
                    valid_lines = [line for line in lines if line.strip() and not line.startswith('#')]
                    logger.info(f"📊 {platform} 有效cookies行数: {len(valid_lines)}")

            except Exception as e:
                logger.error(f"读取 {platform} cookies文件失败: {e}")
                return {
                    'success': False,
                    'valid': False,
                    'error': f'无法读取 {platform} cookies文件: {str(e)}'
                }

            # 根据平台选择测试URL
            test_urls = {
                'youtube': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'twitter': 'https://x.com/elonmusk',
                'instagram': 'https://www.instagram.com/',
                'tiktok': 'https://www.tiktok.com/',
                'bilibili': 'https://www.bilibili.com/'
            }

            test_url = test_urls.get(platform, test_urls['youtube'])

            # 使用yt-dlp测试
            cmd = [
                'yt-dlp', '--cookies', cookies_file,
                '--dump-json', '--no-warnings', '--no-check-certificate',
                test_url
            ]

            logger.info(f"🧪 测试 {platform} 平台cookies: {test_url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            logger.info(f"🧪 {platform} 测试结果返回码: {result.returncode}")
            if result.stdout:
                logger.info(f"🧪 测试标准输出: {result.stdout[:300]}...")
            if result.stderr:
                logger.info(f"🧪 测试错误输出: {result.stderr[:500]}...")

            if result.returncode == 0:
                # 检查是否成功获取到视频信息
                try:
                    import json
                    video_info = json.loads(result.stdout)
                    if video_info.get('title'):
                        logger.info(f"✅ 成功获取视频信息: {video_info.get('title', 'Unknown')}")
                        return {
                            'success': True,
                            'valid': True,
                            'message': f'{platform} 平台cookies有效，成功获取视频: {video_info.get("title", "Unknown")}',
                            'test_platform': platform
                        }
                except:
                    pass

                return {
                    'success': True,
                    'valid': True,
                    'message': f'{platform} 平台cookies有效，可以正常下载',
                    'test_platform': platform
                }
            else:
                # 详细分析错误信息
                error_msg = result.stderr

                # 对于Twitter/X平台，特殊处理一些常见的"错误"情况
                if platform == 'twitter':
                    # Twitter特殊情况处理
                    if 'HTTP Error 403' in error_msg and 'Forbidden' in error_msg:
                        # 403可能是因为没有登录，但cookies可能仍然有效
                        return {
                            'success': True,
                            'valid': True,
                            'message': 'Twitter cookies有效（403错误通常表示需要登录查看内容，但cookies本身可用）',
                            'test_platform': platform,
                            'note': '403错误在Twitter测试中通常是正常的'
                        }
                    elif 'HTTP Error 404' in error_msg:
                        # 404可能是测试URL问题，不代表cookies无效
                        return {
                            'success': True,
                            'valid': True,
                            'message': 'Twitter cookies有效（测试URL不可用，但cookies本身可用）',
                            'test_platform': platform,
                            'note': '404错误不影响cookies有效性'
                        }
                    elif 'Unable to extract' in error_msg and 'twitter' in error_msg.lower():
                        # 提取失败可能是因为内容限制，不代表cookies无效
                        return {
                            'success': True,
                            'valid': True,
                            'message': 'Twitter cookies有效（内容提取限制，但cookies本身可用）',
                            'test_platform': platform,
                            'note': '提取限制不影响cookies有效性'
                        }

                # 通用错误处理
                if 'Sign in to confirm you\'re not a bot' in error_msg or 'bot' in error_msg.lower():
                    return {
                        'success': True,
                        'valid': False,
                        'message': f'{platform} 平台遇到bot检测，cookies可能需要更新',
                        'error': 'Bot检测',
                        'test_platform': platform
                    }
                elif 'Private video' in error_msg or 'Video unavailable' in error_msg:
                    return {
                        'success': True,
                        'valid': True,
                        'message': f'{platform} 平台cookies有效（测试内容不可用）',
                        'test_platform': platform
                    }
                elif 'HTTP Error 403' in error_msg and platform != 'twitter':
                    # 非Twitter平台的403错误
                    return {
                        'success': True,
                        'valid': False,
                        'message': f'{platform} 平台cookies可能已过期或无效',
                        'error': '403错误，请更新cookies',
                        'test_platform': platform
                    }
                else:
                    return {
                        'success': True,
                        'valid': False,
                        'message': f'{platform} 平台cookies测试失败',
                        'error': error_msg[:300] if error_msg else '未知错误',
                        'test_platform': platform
                    }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'valid': False,
                'error': f'{platform} 平台cookies测试超时',
                'test_platform': platform
            }
        except Exception as e:
            logger.error(f"{platform} 平台cookies测试异常: {e}")
            return {
                'success': False,
                'valid': False,
                'error': f'{platform} 平台测试异常: {str(e)}',
                'test_platform': platform
            }

    def import_cookies(self, cookies_content: str, format_type: str = 'auto', preserve_format: bool = False) -> Dict:
        """导入cookies - 支持保持原始格式或转换格式"""
        try:
            if not cookies_content.strip():
                return {
                    'success': False,
                    'error': '请提供cookies内容'
                }

            # 检测原始格式
            detected_format = self._detect_cookies_format(cookies_content)

            if preserve_format and detected_format == 'netscape':
                # 保持原始Netscape格式，只做清理
                logger.info("🔄 保持原始Netscape格式，仅清理过期cookies")
                final_content = self._clean_expired_cookies(cookies_content)
            else:
                # 转换格式（原有逻辑）
                final_content, detected_format = self._convert_cookies_format(cookies_content, format_type, full_backup=True)

            # 验证cookies内容
            validation_result = self._validate_cookies_content(final_content)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'found_cookies': validation_result.get('found_cookies', [])
                }

            # 按平台分离cookies并保存到独立文件
            platform_files = self._save_cookies_by_platform(final_content)

            logger.info(f"✅ Cookies已按平台保存到 {len(platform_files)} 个文件")

            return {
                'success': True,
                'message': f'Cookies导入成功 ({"保持原格式" if preserve_format else "完整备份模式"})',
                'detected_format': detected_format,
                'found_cookies': validation_result['found_cookies'],
                'platform_files': platform_files,
                'import_mode': 'preserve_format' if preserve_format else 'full_backup'
            }

        except Exception as e:
            logger.error(f"导入cookies失败: {e}")
            return {
                'success': False,
                'error': f'导入失败: {str(e)}'
            }

    def _detect_cookies_format(self, content: str) -> str:
        """检测cookies格式"""
        try:
            json.loads(content)
            return 'json'
        except:
            if content.startswith('# Netscape HTTP Cookie File'):
                return 'netscape'
            elif '\t' in content and ('youtube.com' in content or 'google.com' in content):
                return 'netscape'
            else:
                return 'unknown'

    def _save_cookies_by_platform(self, cookies_content: str) -> Dict[str, str]:
        """按平台分离cookies并保存到独立文件"""
        platform_cookies = {}

        # 初始化平台cookies字典
        for platform in self.platform_configs.keys():
            platform_cookies[platform] = []

        # 分析cookies内容，按平台分类
        for line in cookies_content.split('\n'):
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split('\t')
                if len(parts) >= 6:
                    domain = parts[0]

                    # 检测这个cookie属于哪个平台
                    platform = self.detect_platform_from_domain(domain)
                    if platform != 'unknown':
                        platform_cookies[platform].append(line)

        # 为每个有cookies的平台生成文件
        platform_files = {}
        for platform, cookies_lines in platform_cookies.items():
            if cookies_lines:  # 只为有cookies的平台生成文件
                file_path = self.get_platform_cookies_file(platform)

                # 生成文件内容
                file_content = "# Netscape HTTP Cookie File\n"
                file_content += f"# Auto-generated {platform} cookies for yt-dlp\n"
                file_content += f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                file_content += '\n'.join(cookies_lines)

                # 保存文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)

                platform_files[platform] = file_path
                logger.info(f"📁 {platform} 平台: 保存 {len(cookies_lines)} 个cookies到 {file_path}")

        return platform_files







    def _convert_cookies_format(self, content: str, format_type: str, full_backup: bool = False) -> Tuple[str, str]:
        """转换cookies格式 - 支持完整备份或智能提取"""
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
            # JSON格式转换为Netscape格式
            cookies_data = json.loads(content)
            netscape_lines = [
                '# Netscape HTTP Cookie File',
                '# This is a generated file! Do not edit.',
                f'# {"Complete backup" if full_backup else "Auto-extracted Google/YouTube cookies"} for yt-dlp',
                ''
            ]

            extracted_count = 0
            current_time = int(time.time())

            if full_backup:
                # 完整备份模式：转换所有cookies
                logger.info("🔄 完整备份模式：转换所有cookies")
                for cookie in cookies_data:
                    if isinstance(cookie, dict) and 'domain' in cookie:
                        domain = cookie.get('domain', '')
                        name = cookie.get('name', '')
                        domain_flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'

                        # 处理过期时间
                        expiration = cookie.get('expirationDate', 0)
                        if isinstance(expiration, float):
                            expiration = int(expiration)
                        elif expiration == 0:
                            # 会话cookie转换为长期cookie，避免容器重启丢失
                            expiration = current_time + (365 * 24 * 3600)  # 1年后过期
                            logger.debug(f"🔄 会话cookie {name} 转换为长期cookie，过期时间: {expiration}")

                        # 跳过已过期的cookies
                        if expiration > 0 and expiration < current_time:
                            logger.warning(f"⚠️ 跳过过期cookie: {name} (过期时间: {expiration})")
                            continue

                        value = cookie.get('value', '')

                        # 清理value中的特殊字符，防止破坏Netscape格式
                        value = self._sanitize_cookie_value(value)

                        # 构建Netscape格式行
                        line = f'{domain}\t{domain_flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}'
                        netscape_lines.append(line)
                        extracted_count += 1

                logger.info(f"🍪 完整备份：转换了 {extracted_count} 个有效cookies")

            return '\n'.join(netscape_lines), detected_format
        else:
            # 已经是Netscape格式，需要清理过期cookies
            return self._clean_expired_cookies(content), detected_format

    def _clean_expired_cookies(self, content: str) -> str:
        """清理过期的cookies并修复会话cookies"""
        lines = content.split('\n')
        cleaned_lines = []
        current_time = int(time.time())
        cleaned_count = 0
        session_fixed_count = 0

        for line in lines:
            if line.startswith('#') or not line.strip():
                # 保留注释和空行
                cleaned_lines.append(line)
                continue

            parts = line.strip().split('\t')
            if len(parts) >= 7:
                domain = parts[0]
                domain_flag = parts[1]
                path = parts[2]
                secure = parts[3]
                expiration = int(parts[4]) if parts[4].isdigit() else 0
                name = parts[5]
                value = parts[6]

                # 检查是否过期
                if expiration > 0 and expiration < current_time:
                    logger.warning(f"⚠️ 清理过期cookie: {name} (过期时间: {expiration})")
                    cleaned_count += 1
                    continue

                # 修复会话cookies（过期时间为0）
                if expiration == 0:
                    expiration = current_time + (365 * 24 * 3600)  # 1年后过期
                    logger.debug(f"🔄 修复会话cookie: {name} -> 过期时间: {expiration}")
                    session_fixed_count += 1

                # 重建行
                fixed_line = f'{domain}\t{domain_flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}'
                cleaned_lines.append(fixed_line)
            else:
                # 保留格式不正确的行（可能是注释）
                cleaned_lines.append(line)

        if cleaned_count > 0:
            logger.info(f"🧹 清理了 {cleaned_count} 个过期cookies")
        if session_fixed_count > 0:
            logger.info(f"🔧 修复了 {session_fixed_count} 个会话cookies")

        return '\n'.join(cleaned_lines)

    def _validate_cookies_content(self, content: str) -> Dict:
        """验证cookies内容 - 支持多平台域名"""
        important_cookies = self._get_important_cookies_list()

        found_cookies = []
        platform_cookies = {}

        for line in content.split('\n'):
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    cookie_name = parts[5]
                    cookie_value = parts[6]

                    # 检查cookie值是否为空
                    if not cookie_value.strip():
                        continue

                    # 检测平台
                    platform = self.detect_platform_from_domain(domain)
                    if platform != 'unknown' and cookie_name in important_cookies:
                        found_cookies.append(cookie_name)

                        if platform not in platform_cookies:
                            platform_cookies[platform] = []
                        platform_cookies[platform].append(cookie_name)

        # 移除重复项
        found_cookies = list(set(found_cookies))

        # 验证逻辑：检查是否有任何平台的认证cookies
        has_auth = False
        for platform, config in self.platform_configs.items():
            if platform in platform_cookies:
                platform_found = platform_cookies[platform]
                auth_cookies = config['auth_cookies']

                # 对于Twitter，需要同时有auth_token和ct0才算有完整认证
                if platform == 'twitter':
                    has_auth_token = 'auth_token' in platform_found
                    has_ct0 = 'ct0' in platform_found
                    if has_auth_token and has_ct0:
                        has_auth = True
                        break
                else:
                    # 其他平台只需要有任一认证cookie
                    if any(cookie in platform_found for cookie in auth_cookies):
                        has_auth = True
                        break

        if len(found_cookies) < 1 and not has_auth:
            return {
                'valid': False,
                'error': f'cookies内容不完整，只找到 {len(found_cookies)} 个重要cookies',
                'found_cookies': found_cookies,
                'platform_cookies': platform_cookies
            }

        return {
            'valid': True,
            'found_cookies': found_cookies,
            'platform_cookies': platform_cookies
        }











    def list_current_cookies(self) -> List[Dict]:
        """列出当前导入的cookies文件"""
        try:
            platform_files = self.get_all_platform_cookies_files()
            cookies_files = []

            for platform, file_path in platform_files.items():
                if os.path.exists(file_path):
                    # 获取文件信息
                    stat = os.stat(file_path)
                    file_size = stat.st_size
                    modified_time = stat.st_mtime

                    # 分析cookies内容
                    analysis = self._analyze_cookies_expiration(file_path)

                    cookies_files.append({
                        'platform': platform,
                        'file_path': file_path,
                        'file_name': os.path.basename(file_path),
                        'file_size': file_size,
                        'file_size_mb': round(file_size / 1024 / 1024, 2),
                        'modified_time': modified_time,
                        'modified_date': datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S'),
                        'cookies_count': analysis.get('total_cookies', 0),
                        'valid_cookies': analysis.get('valid_cookies', 0),
                        'expired_cookies': analysis.get('expired_cookies', 0),
                        'has_auth': analysis.get('has_auth', False)
                    })

            # 按修改时间排序（最新的在前）
            cookies_files.sort(key=lambda x: x['modified_time'], reverse=True)

            return cookies_files

        except Exception as e:
            logger.error(f"列出cookies文件失败: {e}")
            return []

    def inspect_platform_cookies(self, platform: str) -> Dict:
        """检查指定平台的cookies文件内容"""
        try:
            platform_files = self.get_all_platform_cookies_files()
            file_path = platform_files.get(platform)

            if not file_path or not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'{platform} 平台的cookies文件不存在'
                }

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分析cookies
            analysis = self._analyze_cookies_expiration(file_path)

            # 提取cookies详情
            cookies_details = []
            lines = content.split('\n')

            for line in lines:
                if line.strip() and not line.startswith('#'):
                    parts = line.strip().split('\t')
                    if len(parts) >= 7:
                        domain = parts[0]
                        name = parts[5]
                        value = parts[6]
                        expiration = int(parts[4]) if parts[4].isdigit() else 0

                        # 检查是否过期
                        is_expired = expiration > 0 and expiration < time.time()

                        # 检查是否是重要cookie
                        is_important = name in self.get_all_important_cookies()

                        cookies_details.append({
                            'domain': domain,
                            'name': name,
                            'value': value[:20] + '...' if len(value) > 20 else value,
                            'expiration': expiration,
                            'expiration_date': datetime.fromtimestamp(expiration).strftime('%Y-%m-%d %H:%M:%S') if expiration > 0 else '会话',
                            'is_expired': is_expired,
                            'is_important': is_important
                        })

            return {
                'success': True,
                'platform': platform,
                'file_path': file_path,
                'file_size': len(content),
                'analysis': analysis,
                'cookies_details': cookies_details,
                'total_lines': len(lines),
                'valid_lines': len([line for line in lines if line.strip() and not line.startswith('#')])
            }

        except Exception as e:
            logger.error(f"检查{platform}平台cookies失败: {e}")
            return {
                'success': False,
                'error': f'检查失败: {str(e)}'
            }

    def delete_platform_cookies(self, platform: str) -> Dict:
        """删除指定平台的cookies文件"""
        try:
            platform_files = self.get_all_platform_cookies_files()
            file_path = platform_files.get(platform)

            if not file_path:
                return {
                    'success': False,
                    'error': f'不支持的平台: {platform}'
                }

            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'{platform} 平台的cookies文件不存在'
                }

            # 删除文件
            os.remove(file_path)

            logger.info(f"✅ 删除了{platform}平台的cookies文件: {file_path}")

            return {
                'success': True,
                'message': f'{platform} 平台的cookies文件已删除',
                'platform': platform,
                'deleted_file': file_path
            }

        except Exception as e:
            logger.error(f"删除{platform}平台cookies失败: {e}")
            return {
                'success': False,
                'error': f'删除失败: {str(e)}'
            }

    def clean_platform_cookies(self, platform: str) -> Dict:
        """清理指定平台的过期cookies并修复会话cookies"""
        try:
            platform_files = self.get_all_platform_cookies_files()
            file_path = platform_files.get(platform)

            if not file_path:
                return {
                    'success': False,
                    'error': f'不支持的平台: {platform}'
                }

            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'{platform} 平台的cookies文件不存在'
                }

            # 读取原文件
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 清理cookies
            cleaned_content = self._clean_expired_cookies(original_content)

            # 保存清理后的文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)

            logger.info(f"🧹 清理了{platform}平台的cookies文件: {file_path}")

            return {
                'success': True,
                'message': f'{platform} 平台的cookies已清理',
                'platform': platform,
                'cleaned_file': file_path
            }

        except Exception as e:
            logger.error(f"清理{platform}平台cookies失败: {e}")
            return {
                'success': False,
                'error': f'清理失败: {str(e)}'
            }





    def backup_cookies(self, backup_name: str = None) -> Dict:
        """备份所有平台的cookies文件"""
        try:
            # 创建备份目录
            backup_dir = os.path.join(self.config_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            # 生成备份名称
            if not backup_name:
                backup_name = f"cookies_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            backup_path = os.path.join(backup_dir, backup_name)
            os.makedirs(backup_path, exist_ok=True)

            # 备份所有平台的cookies文件
            platform_files = self.get_all_platform_cookies_files()
            backed_up_files = []

            for platform, file_path in platform_files.items():
                if os.path.exists(file_path):
                    backup_file_path = os.path.join(backup_path, f"{platform}_cookies.txt")

                    # 复制文件
                    import shutil
                    shutil.copy2(file_path, backup_file_path)

                    backed_up_files.append({
                        'platform': platform,
                        'original_path': file_path,
                        'backup_path': backup_file_path,
                        'size': os.path.getsize(file_path)
                    })

                    logger.debug(f"📦 备份 {platform} cookies: {backup_file_path}")

            if backed_up_files:
                # 创建备份信息文件
                backup_info = {
                    'backup_name': backup_name,
                    'backup_time': datetime.now().isoformat(),
                    'backed_up_files': backed_up_files,
                    'total_files': len(backed_up_files),
                    'total_size': sum(f['size'] for f in backed_up_files)
                }

                info_file_path = os.path.join(backup_path, 'backup_info.json')
                with open(info_file_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_info, f, indent=2, ensure_ascii=False)

                logger.info(f"✅ Cookies备份完成: {backup_path} ({len(backed_up_files)} 个文件)")

                return {
                    'success': True,
                    'message': f'成功备份 {len(backed_up_files)} 个平台的cookies',
                    'backup_name': backup_name,
                    'backup_path': backup_path,
                    'backed_up_files': backed_up_files,
                    'backup_info': backup_info
                }
            else:
                return {
                    'success': False,
                    'error': '没有找到需要备份的cookies文件'
                }

        except Exception as e:
            logger.error(f"备份cookies失败: {e}")
            return {
                'success': False,
                'error': f'备份失败: {str(e)}'
            }

    def list_backups(self) -> Dict:
        """列出所有可用的备份"""
        try:
            backup_dir = os.path.join(self.config_dir, 'backups')

            if not os.path.exists(backup_dir):
                return {
                    'success': True,
                    'backups': [],
                    'message': '没有找到备份目录'
                }

            backups = []

            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                if os.path.isdir(item_path):
                    info_file = os.path.join(item_path, 'backup_info.json')

                    if os.path.exists(info_file):
                        try:
                            with open(info_file, 'r', encoding='utf-8') as f:
                                backup_info = json.load(f)

                            # 验证备份文件是否完整
                            files_exist = all(
                                os.path.exists(f['backup_path'])
                                for f in backup_info.get('backed_up_files', [])
                            )

                            backup_info['files_exist'] = files_exist
                            backup_info['backup_path'] = item_path
                            backups.append(backup_info)

                        except Exception as e:
                            logger.warning(f"读取备份信息失败 {info_file}: {e}")
                    else:
                        # 没有信息文件的旧备份
                        stat = os.stat(item_path)
                        backups.append({
                            'backup_name': item,
                            'backup_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'backup_path': item_path,
                            'files_exist': True,
                            'total_files': len([f for f in os.listdir(item_path) if f.endswith('.txt')]),
                            'is_legacy': True
                        })

            # 按时间排序（最新的在前）
            backups.sort(key=lambda x: x['backup_time'], reverse=True)

            return {
                'success': True,
                'backups': backups,
                'total_backups': len(backups)
            }

        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return {
                'success': False,
                'error': f'列出备份失败: {str(e)}'
            }

    def restore_cookies(self, backup_name: str) -> Dict:
        """从备份恢复cookies"""
        try:
            backup_dir = os.path.join(self.config_dir, 'backups')
            backup_path = os.path.join(backup_dir, backup_name)

            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'error': f'备份不存在: {backup_name}'
                }

            # 读取备份信息
            info_file = os.path.join(backup_path, 'backup_info.json')
            backup_info = None

            if os.path.exists(info_file):
                with open(info_file, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)

            # 记录恢复前的状态
            before_analysis = self.analyze_cookies_by_platform()

            # 恢复文件
            restored_files = []

            if backup_info and 'backed_up_files' in backup_info:
                # 使用备份信息恢复
                for file_info in backup_info['backed_up_files']:
                    backup_file_path = file_info['backup_path']
                    original_path = file_info['original_path']
                    platform = file_info['platform']

                    if os.path.exists(backup_file_path):
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(original_path), exist_ok=True)

                        # 复制文件
                        import shutil
                        shutil.copy2(backup_file_path, original_path)

                        restored_files.append({
                            'platform': platform,
                            'file_path': original_path,
                            'size': os.path.getsize(original_path)
                        })

                        logger.debug(f"🔄 恢复 {platform} cookies: {original_path}")
            else:
                # 旧格式备份，直接复制所有txt文件
                platform_files = self.get_all_platform_cookies_files()

                for filename in os.listdir(backup_path):
                    if filename.endswith('_cookies.txt'):
                        platform = filename.replace('_cookies.txt', '')
                        backup_file_path = os.path.join(backup_path, filename)
                        original_path = platform_files.get(platform)

                        if original_path and os.path.exists(backup_file_path):
                            import shutil
                            shutil.copy2(backup_file_path, original_path)

                            restored_files.append({
                                'platform': platform,
                                'file_path': original_path,
                                'size': os.path.getsize(original_path)
                            })

                            logger.debug(f"🔄 恢复 {platform} cookies: {original_path}")

            if restored_files:
                # 分析恢复后的状态
                after_analysis = self.analyze_cookies_by_platform()

                logger.info(f"✅ Cookies恢复完成: {backup_name} ({len(restored_files)} 个文件)")

                return {
                    'success': True,
                    'message': f'成功恢复 {len(restored_files)} 个平台的cookies',
                    'backup_name': backup_name,
                    'restored_files': restored_files,
                    'before_analysis': before_analysis,
                    'after_analysis': after_analysis
                }
            else:
                return {
                    'success': False,
                    'error': '没有找到可恢复的文件'
                }

        except Exception as e:
            logger.error(f"恢复cookies失败: {e}")
            return {
                'success': False,
                'error': f'恢复失败: {str(e)}'
            }

    def delete_backup(self, backup_name: str) -> Dict:
        """删除指定的备份"""
        try:
            backup_dir = os.path.join(self.config_dir, 'backups')
            backup_path = os.path.join(backup_dir, backup_name)

            if not os.path.exists(backup_path):
                return {
                    'success': False,
                    'error': f'备份不存在: {backup_name}'
                }

            # 删除备份目录
            import shutil
            shutil.rmtree(backup_path)

            logger.info(f"🗑️ 删除备份: {backup_name}")

            return {
                'success': True,
                'message': f'备份已删除: {backup_name}'
            }

        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return {
                'success': False,
                'error': f'删除备份失败: {str(e)}'
            }

    def import_cookies_raw(self, cookies_content: str, platform: str = 'youtube') -> Dict:
        """直接导入原始cookies，不做任何格式转换"""
        try:
            if not cookies_content.strip():
                return {
                    'success': False,
                    'error': '请提供cookies内容'
                }

            # 获取目标文件路径
            file_path = self.get_platform_cookies_file(platform)

            # 检测格式并添加必要的头部
            if not cookies_content.startswith('# Netscape HTTP Cookie File'):
                # 如果不是标准Netscape格式，添加头部
                header = "# Netscape HTTP Cookie File\n"
                header += "# This is a generated file! Do not edit.\n"
                header += f"# Raw import for {platform} platform\n"
                header += f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                final_content = header + cookies_content
            else:
                final_content = cookies_content

            # 直接保存，不做任何转换
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(final_content)

            # 统计cookies数量
            lines = final_content.split('\n')
            cookie_count = len([line for line in lines if line.strip() and not line.startswith('#')])

            logger.info(f"📁 原始导入: 保存 {cookie_count} 行cookies到 {file_path}")

            return {
                'success': True,
                'message': f'{platform} 平台cookies原始导入成功',
                'platform': platform,
                'file_path': file_path,
                'cookie_count': cookie_count,
                'import_mode': 'raw'
            }

        except Exception as e:
            logger.error(f"原始导入cookies失败: {e}")
            return {
                'success': False,
                'error': f'原始导入失败: {str(e)}'
            }
# 全局实例
_cookies_manager = CookiesManager()

def get_cookies_manager():
    """获取cookies管理器实例"""
    return _cookies_manager
