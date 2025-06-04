"""
自定义视频提取器
支持特定网站的视频提取，如missav.ai等
"""

import re
import json
import logging
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class MissavExtractor:
    """Missav.ai 视频提取器"""
    
    IE_NAME = 'missav'
    IE_DESC = 'Missav.ai videos'
    
    # 支持的URL模式
    _VALID_URL_PATTERNS = [
        r'https?://(?:www\.)?missav\.ai/(?:cn/)?(?P<id>[a-zA-Z0-9\-]+)',
        r'https?://(?:www\.)?missav\.com/(?:cn/)?(?P<id>[a-zA-Z0-9\-]+)',
    ]
    
    def __init__(self):
        self.session = requests.Session()
        # 使用更真实的浏览器头部来绕过Cloudflare
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Connection': 'keep-alive',
        })

        # 添加重试机制
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 禁用 SSL 验证警告（仅用于绕过某些网站的 SSL 问题）
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # 设置更长的超时时间
        self.session.timeout = 30
    
    def suitable(self, url):
        """检查URL是否适用于此提取器"""
        for pattern in self._VALID_URL_PATTERNS:
            if re.match(pattern, url):
                return True
        return False
    
    def extract_info(self, url):
        """提取视频信息"""
        try:
            logger.info(f"🎬 开始提取 Missav 视频: {url}")

            # 尝试多种方法获取网页内容
            response = self._get_webpage_with_retry(url)

            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取基本信息
            title = self._extract_title(soup, url)
            video_id = self._extract_video_id(url)

            # 提取视频流URL
            video_urls = self._extract_video_urls(soup, response.text, url)

            if not video_urls:
                # 如果没有找到视频URL，尝试使用yt-dlp作为备用
                logger.warning("自定义提取器未找到视频流，尝试使用yt-dlp备用方案")
                return self._fallback_to_ytdlp(url)

            # 构建结果
            result = {
                'id': video_id,
                'title': title,
                'url': url,
                'formats': video_urls,
                'extractor': 'missav',
                'webpage_url': url,
                'description': self._extract_description(soup),
                'thumbnail': self._extract_thumbnail(soup, url),
                'duration': self._extract_duration(soup),
                'uploader': 'Missav',
                'uploader_id': 'missav',
            }

            logger.info(f"✅ 成功提取视频信息: {title}")
            return result

        except Exception as e:
            logger.error(f"❌ 提取视频信息失败: {e}")
            # 尝试使用yt-dlp作为最后的备用方案
            logger.info("🔄 尝试使用yt-dlp备用方案")
            try:
                return self._fallback_to_ytdlp(url)
            except Exception as fallback_error:
                logger.error(f"❌ yt-dlp备用方案也失败: {fallback_error}")
                raise Exception(f"Missav提取失败: {str(e)}")

    def _get_webpage_with_retry(self, url):
        """使用多种策略获取网页内容"""
        strategies = [
            self._get_with_chrome_headers,
            self._get_with_firefox_headers,
            self._get_with_mobile_headers,
            self._get_with_edge_headers,
            self._get_with_delay_and_chrome,
            self._get_with_aggressive_bypass,
            self._get_with_standard_headers,
        ]

        last_error = None

        for i, strategy in enumerate(strategies):
            try:
                logger.info(f"🔄 尝试策略 {i+1}: {strategy.__name__}")
                response = strategy(url)

                # 检查是否被Cloudflare阻止
                if self._is_cloudflare_blocked(response):
                    logger.warning(f"⚠️ 策略 {i+1} 被Cloudflare阻止")
                    continue

                logger.info(f"✅ 策略 {i+1} 成功")
                return response

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ 策略 {i+1} 失败: {e}")
                continue

        raise last_error or Exception("所有获取策略都失败")

    def _get_with_standard_headers(self, url):
        """使用标准头部获取"""
        return self.session.get(url, timeout=30)

    def _get_with_chrome_headers(self, url):
        """使用Chrome浏览器头部获取"""
        chrome_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
        return self.session.get(url, headers=chrome_headers, timeout=30)

    def _get_with_firefox_headers(self, url):
        """使用Firefox浏览器头部获取"""
        firefox_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        return self.session.get(url, headers=firefox_headers, timeout=30)

    def _get_with_mobile_headers(self, url):
        """使用移动端头部获取"""
        mobile_headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        return self.session.get(url, headers=mobile_headers, timeout=30)

    def _get_with_edge_headers(self, url):
        """使用Edge浏览器头部获取"""
        edge_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
        return self.session.get(url, headers=edge_headers, timeout=30)

    def _get_with_delay_and_chrome(self, url):
        """添加延迟后使用Chrome头部获取"""
        import time
        time.sleep(3)  # 等待3秒

        chrome_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        return self.session.get(url, headers=chrome_headers, timeout=30)

    def _get_with_aggressive_bypass(self, url):
        """使用激进的绕过策略"""
        import time
        import random

        # 随机延迟
        time.sleep(random.uniform(2, 5))

        # 使用最新的Chrome头部，模拟真实浏览器行为
        aggressive_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1',
            'Connection': 'keep-alive',
            # 添加一些额外的头部来模拟真实浏览器
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Real-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
        }

        # 创建新的session来避免cookie污染
        temp_session = requests.Session()
        temp_session.headers.update(aggressive_headers)

        # 设置重试机制
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=2,
            backoff_factor=2,
            status_forcelist=[403, 429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        temp_session.mount("http://", adapter)
        temp_session.mount("https://", adapter)

        try:
            # 禁用SSL验证（仅在必要时）
            response = temp_session.get(url, timeout=45, verify=False)
            return response
        finally:
            temp_session.close()

    def _is_cloudflare_blocked(self, response):
        """检查是否被Cloudflare阻止"""
        # 检查状态码
        if response.status_code in [403, 503, 429]:
            return True

        # 检查响应头
        cf_headers = ['cf-ray', 'cf-cache-status', 'server']
        for header in cf_headers:
            if header in response.headers:
                header_value = response.headers[header].lower()
                if 'cloudflare' in header_value or 'cf-' in header_value:
                    return True

        # 检查响应内容中的Cloudflare标识
        content_lower = response.text.lower()
        cloudflare_indicators = [
            'cloudflare',
            'checking your browser',
            'ddos protection',
            'ray id',
            'cf-ray',
            'please wait while we are checking your browser',
            'browser check',
            'security check',
            'just a moment',
            'enable javascript and cookies',
            'attention required',
            'cloudflare to restrict access',
        ]

        # 检查页面长度，Cloudflare 阻止页面通常很短
        if len(response.text) < 1000 and any(indicator in content_lower for indicator in cloudflare_indicators):
            return True

        return any(indicator in content_lower for indicator in cloudflare_indicators)

    def _fallback_to_ytdlp(self, url):
        """使用yt-dlp作为备用方案"""
        try:
            from .ytdlp_manager import get_ytdlp_manager

            ytdlp_manager = get_ytdlp_manager()

            # 尝试多种yt-dlp配置
            configs = [
                # 配置1: 使用impersonation（如果可用）
                {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'skip_download': True,
                    'extractor_args': {
                        'generic': {
                            'impersonate': 'chrome'
                        }
                    }
                },
                # 配置2: 使用自定义头部
                {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'skip_download': True,
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Accept-Encoding': 'gzip, deflate, br',
                    }
                },
                # 配置3: 基础配置
                {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'skip_download': True,
                }
            ]

            last_error = None

            for i, ydl_opts in enumerate(configs):
                try:
                    logger.info(f"🔄 尝试yt-dlp配置 {i+1}")

                    with ytdlp_manager.create_downloader(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)

                        if info:
                            logger.info(f"✅ yt-dlp配置 {i+1} 成功")
                            return info

                except Exception as e:
                    last_error = e
                    logger.warning(f"⚠️ yt-dlp配置 {i+1} 失败: {e}")
                    continue

            raise last_error or Exception("所有yt-dlp配置都失败")

        except Exception as e:
            logger.error(f"❌ yt-dlp备用方案失败: {e}")
            # 如果yt-dlp也失败，返回一个基础的信息结构
            return self._create_fallback_info(url)

    def _create_fallback_info(self, url):
        """创建备用信息结构"""
        video_id = self._extract_video_id(url)

        # 创建一个基础的信息结构，让用户知道需要手动处理
        return {
            'id': video_id,
            'title': f"Missav_{video_id}",
            'url': url,
            'formats': [],  # 空格式列表，表示需要手动处理
            'extractor': 'missav_fallback',
            'webpage_url': url,
            'description': '由于网站保护机制，无法自动提取视频信息。请尝试手动下载或稍后重试。',
            'thumbnail': None,
            'duration': None,
            'uploader': 'Missav',
            'uploader_id': 'missav',
            '_fallback': True,  # 标记为备用信息
        }

    def _extract_title(self, soup, url):
        """提取视频标题"""
        # 尝试多种方式提取标题
        title_selectors = [
            'h1.text-secondary',
            'h1',
            '.video-title',
            'title',
            'meta[property="og:title"]',
            'meta[name="title"]'
        ]
        
        for selector in title_selectors:
            try:
                if selector.startswith('meta'):
                    element = soup.select_one(selector)
                    if element:
                        title = element.get('content', '').strip()
                        if title:
                            return self._clean_title(title)
                else:
                    element = soup.select_one(selector)
                    if element:
                        title = element.get_text().strip()
                        if title:
                            return self._clean_title(title)
            except Exception as e:
                logger.debug(f"标题提取失败 ({selector}): {e}")
                continue
        
        # 如果都失败了，从URL提取
        video_id = self._extract_video_id(url)
        return f"Missav_{video_id}"
    
    def _clean_title(self, title):
        """清理标题"""
        # 移除网站名称
        title = re.sub(r'\s*-\s*MISSAV.*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\|\s*MISSAV.*$', '', title, flags=re.IGNORECASE)
        
        # 清理特殊字符
        title = re.sub(r'[<>:"/\\|?*]', '_', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title or "Missav_Video"
    
    def _extract_video_id(self, url):
        """从URL提取视频ID"""
        for pattern in self._VALID_URL_PATTERNS:
            match = re.match(pattern, url)
            if match:
                return match.group('id')
        
        # 备用方法：从URL路径提取
        path = urlparse(url).path
        video_id = path.split('/')[-1]
        return video_id or 'unknown'
    
    def _extract_video_urls(self, soup, html_content, page_url):
        """提取视频流URL"""
        video_urls = []
        
        # 方法1: 查找JavaScript中的播放列表URL
        m3u8_patterns = [
            r'["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'playlist\s*:\s*["\']([^"\']+)["\']',
            r'src\s*:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
            r'file\s*:\s*["\']([^"\']*\.m3u8[^"\']*)["\']',
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if '.m3u8' in match:
                    # 转换为绝对URL
                    if match.startswith('http'):
                        video_url = match
                    else:
                        video_url = urljoin(page_url, match)
                    
                    video_urls.append({
                        'url': video_url,
                        'format_id': 'hls',
                        'ext': 'mp4',
                        'protocol': 'm3u8',
                        'quality': 'unknown'
                    })
                    logger.info(f"🎯 找到视频流: {video_url}")
        
        # 方法2: 查找video标签
        video_tags = soup.find_all('video')
        for video in video_tags:
            src = video.get('src')
            if src and ('.m3u8' in src or '.mp4' in src):
                if not src.startswith('http'):
                    src = urljoin(page_url, src)
                
                video_urls.append({
                    'url': src,
                    'format_id': 'direct',
                    'ext': 'mp4',
                    'quality': 'unknown'
                })
        
        # 方法3: 查找source标签
        source_tags = soup.find_all('source')
        for source in source_tags:
            src = source.get('src')
            if src and ('.m3u8' in src or '.mp4' in src):
                if not src.startswith('http'):
                    src = urljoin(page_url, src)
                
                video_urls.append({
                    'url': src,
                    'format_id': 'source',
                    'ext': 'mp4',
                    'quality': 'unknown'
                })
        
        # 去重
        seen_urls = set()
        unique_urls = []
        for video_url in video_urls:
            if video_url['url'] not in seen_urls:
                seen_urls.add(video_url['url'])
                unique_urls.append(video_url)
        
        return unique_urls
    
    def _extract_description(self, soup):
        """提取视频描述"""
        desc_selectors = [
            'meta[property="og:description"]',
            'meta[name="description"]',
            '.video-description',
            '.description'
        ]
        
        for selector in desc_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if selector.startswith('meta'):
                        desc = element.get('content', '').strip()
                    else:
                        desc = element.get_text().strip()
                    
                    if desc:
                        return desc
            except:
                continue
        
        return None
    
    def _extract_thumbnail(self, soup, page_url):
        """提取缩略图"""
        thumb_selectors = [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
            'video[poster]',
            '.video-thumbnail img',
            '.thumbnail img'
        ]
        
        for selector in thumb_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if selector.startswith('meta'):
                        thumb = element.get('content', '').strip()
                    elif 'poster' in selector:
                        thumb = element.get('poster', '').strip()
                    else:
                        thumb = element.get('src', '').strip()
                    
                    if thumb:
                        if not thumb.startswith('http'):
                            thumb = urljoin(page_url, thumb)
                        return thumb
            except:
                continue
        
        return None
    
    def _extract_duration(self, soup):
        """提取视频时长"""
        duration_selectors = [
            'meta[property="video:duration"]',
            '.duration',
            '.video-duration'
        ]
        
        for selector in duration_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if selector.startswith('meta'):
                        duration_str = element.get('content', '').strip()
                    else:
                        duration_str = element.get_text().strip()
                    
                    if duration_str:
                        # 尝试解析时长
                        return self._parse_duration(duration_str)
            except:
                continue
        
        return None
    
    def _parse_duration(self, duration_str):
        """解析时长字符串"""
        try:
            # 格式: "MM:SS" 或 "HH:MM:SS"
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 2:  # MM:SS
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:  # HH:MM:SS
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            
            # 格式: 纯数字（秒）
            return int(duration_str)
        except:
            return None


# 全局提取器实例
missav_extractor = MissavExtractor()


def get_custom_extractor(url):
    """根据URL获取合适的自定义提取器"""
    if missav_extractor.suitable(url):
        return missav_extractor
    
    return None


def extract_with_custom_extractor(url):
    """使用自定义提取器提取视频信息"""
    extractor = get_custom_extractor(url)
    if extractor:
        return extractor.extract_info(url)
    
    raise Exception(f"没有找到适合的自定义提取器: {url}")
