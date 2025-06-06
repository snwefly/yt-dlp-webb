# -*- coding: utf-8 -*-
"""
API 路由 - 视频信息和下载相关
"""

from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from ..core.ytdlp_manager import get_ytdlp_manager
from ..core.download_manager import get_download_manager
from ..core.error_handler import success_response, error_response, ValidationError, NotFoundError
from ..utils import validate_url
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

@api_bp.route('/info', methods=['GET', 'POST'])
def get_video_info():
    """获取视频信息而不下载"""
    try:
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return error_response('yt-dlp 服务不可用', 503)

        # 支持 GET 和 POST 两种方法
        if request.method == 'GET':
            # GET 请求从查询参数获取 URL
            url = request.args.get('url')
            if not url:
                return error_response('需要提供 URL 参数', 400)
        else:
            # POST 请求从 JSON 数据获取 URL
            data = request.get_json()
            if not data or 'url' not in data:
                return error_response('需要提供 URL', 400)
            url = data['url']

        url = url.strip()

        # 验证URL安全性
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
            return error_response(f'URL验证失败: {error_msg}', 400)

        # YouTube cookies检查
        if 'youtube.com' in url or 'youtu.be' in url:
            from ..core.cookies_manager import get_cookies_manager
            cookies_manager = get_cookies_manager()
            status = cookies_manager.get_status()

            if not status['exists'] or status['status'] in ['expired', 'incomplete']:
                return error_response(
                    'YouTube视频需要有效的cookies认证',
                    400,
                    {
                        'solution': '请在管理页面导入有效的YouTube cookies',
                        'cookies_status': status['status'],
                        'message': status['message']
                    }
                )

        # 最简配置 - 让yt-dlp使用默认行为
        ydl_opts = {
            'quiet': True,
            'skip_download': True,  # 只获取信息，不下载
            # 让yt-dlp使用所有默认设置，包括自动处理YouTube等网站
        }

        # 合并增强配置
        enhanced_opts = ytdlp_manager.get_enhanced_options()
        ydl_opts.update(enhanced_opts)

        # 尝试多种策略获取视频信息
        info = None
        last_error = None

        # 策略1: 使用自定义提取器（优先）
        try:
            info = ytdlp_manager.extract_info_with_custom(url, ydl_opts)
            logger.info("✅ 自定义提取器成功获取视频信息")
        except Exception as e:
            last_error = e
            logger.warning(f"自定义提取器失败: {str(e)}")

            # 策略2: 使用yt-dlp默认配置
            try:
                with ytdlp_manager.create_downloader(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                logger.info("✅ yt-dlp默认配置成功获取视频信息")
            except Exception as e2:
                last_error = e2
                logger.warning(f"yt-dlp默认配置失败: {str(e2)}")

                # 策略3: 使用基础配置
                try:
                    basic_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'skip_download': True,
                    }
                    with ytdlp_manager.create_downloader(basic_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    logger.info("✅ yt-dlp基础配置成功获取视频信息")
                except Exception as e3:
                    last_error = e3
                    logger.error(f"所有策略都失败: {str(e3)}")

        if not info:
            raise last_error or Exception("无法获取视频信息")

        # 检查是否为fallback信息
        if info.get('_fallback'):
            return jsonify({
                'success': False,
                'error': info.get('description', '无法提取视频信息'),
                'fallback': True,
                'info': {
                    'title': info.get('title', 'Unknown Video'),
                    'url': url,
                    'message': '由于网站保护机制，无法自动提取视频信息。建议：\n1. 稍后重试\n2. 检查网络连接\n3. 使用其他下载工具'
                }
            })

        # 返回相关信息
        result = {
            'title': info.get('title'),
            'description': info.get('description'),
            'duration': info.get('duration'),
            'uploader': info.get('uploader'),
            'upload_date': info.get('upload_date'),
            'view_count': info.get('view_count'),
            'thumbnail': info.get('thumbnail'),
            'extractor': info.get('extractor', 'unknown'),
        }

        # 处理格式信息
        if 'formats' in info:
            formats = []
            for fmt in info['formats'][:20]:  # 限制格式数量
                if fmt.get('vcodec') != 'none' or fmt.get('acodec') != 'none':
                    formats.append({
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'quality': fmt.get('format_note', ''),
                        'filesize': fmt.get('filesize'),
                        'vcodec': fmt.get('vcodec'),
                        'acodec': fmt.get('acodec'),
                        'resolution': fmt.get('resolution')
                    })
            result['formats'] = formats

        return success_response(result, '视频信息获取成功')

    except Exception as e:
        error_msg = str(e)
        if 'Unsupported URL' in error_msg:
            return jsonify({'success': False, 'error': '不支持的URL或网站'}), 400
        elif 'Video unavailable' in error_msg:
            return jsonify({'success': False, 'error': '视频不可用或已被删除'}), 400
        elif 'Private video' in error_msg:
            return jsonify({'success': False, 'error': '私有视频，无法访问'}), 400
        else:
            logger.error(f"获取视频信息时发生错误: {e}")
            return jsonify({'success': False, 'error': f'获取视频信息失败: {error_msg}'}), 400

@api_bp.route('/download', methods=['POST'])
def start_download():
    """开始视频下载"""
    try:
        logger.info(f"🎬 下载请求")
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return jsonify({'error': 'yt-dlp 服务不可用'}), 503

        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': '需要提供 URL'}), 400

        url = data['url'].strip()

        # 验证URL安全性
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
            return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

        # 添加Telegram推送选项到下载选项中
        # Web端：用户可以自定义是否推送
        telegram_push = data.get('telegram_push', False)  # Web端默认不强制
        telegram_push_mode = data.get('telegram_push_mode', 'file')

        data['telegram_push'] = telegram_push
        data['telegram_push_mode'] = telegram_push_mode

        logger.info(f"🌐 Web端下载 - Telegram推送: enabled={telegram_push}, mode={telegram_push_mode}")

        # 创建下载任务
        download_manager = get_download_manager(current_app)
        download_id = download_manager.create_download(url, data)

        return jsonify({
            'success': True,
            'message': '下载已开始',
            'download_id': download_id,
            'telegram_push_enabled': telegram_push
        })

    except Exception as e:
        logger.error(f"开始下载时发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/download/<download_id>/status')
def get_download_status(download_id):
    """获取下载状态"""
    download_manager = get_download_manager(current_app)
    download = download_manager.get_download(download_id)

    if not download:
        return jsonify({'error': '下载任务不存在'}), 404

    return jsonify(download)

@api_bp.route('/downloads')
def list_downloads():
    """列出所有下载"""
    download_manager = get_download_manager(current_app)
    downloads = download_manager.get_all_downloads()
    return jsonify({'downloads': downloads})

@api_bp.route('/download/<download_id>/file')
def download_file_by_id(download_id):
    """通过下载ID获取文件"""
    try:
        download_manager = get_download_manager(current_app)
        download = download_manager.get_download(download_id)

        if not download:
            return jsonify({'error': '下载任务不存在'}), 404

        if download.get('status') != 'completed':
            return jsonify({'error': '下载尚未完成'}), 400

        file_path = download.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        filename = download.get('filename', 'download')

        # 返回文件
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return jsonify({'error': '文件下载失败'}), 500

@api_bp.route('/downloads/<filename>')
def download_file_by_name(filename):
    """通过文件名下载文件（兼容旧接口）"""
    try:
        download_folder = current_app.config['DOWNLOAD_FOLDER']
        file_path = os.path.join(download_folder, filename)

        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        # 检查是否为视频文件，如果是则允许在浏览器中播放
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension in video_extensions:
            # 视频文件：不强制下载，允许在浏览器中播放
            mime_types = {
                '.mp4': 'video/mp4',
                '.webm': 'video/webm',
                '.ogv': 'video/ogg',
                '.avi': 'video/x-msvideo',
                '.mov': 'video/quicktime',
                '.wmv': 'video/x-ms-wmv',
                '.flv': 'video/x-flv',
                '.mkv': 'video/x-matroska',
                '.m4v': 'video/mp4',
                '.3gp': 'video/3gpp'
            }
            mimetype = mime_types.get(file_extension, 'video/mp4')

            return send_file(
                file_path,
                as_attachment=False,  # 不强制下载
                mimetype=mimetype,
                conditional=True  # 支持范围请求
            )
        else:
            # 非视频文件：正常下载
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )

    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return jsonify({'error': '文件下载失败'}), 500

@api_bp.route('/files')
@login_required
def list_files():
    """列出所有已下载的文件"""
    try:
        download_manager = get_download_manager(current_app)
        files = download_manager.list_downloaded_files()

        # 格式化文件大小
        for file_info in files:
            size_bytes = file_info.get('file_size', 0)
            if size_bytes:
                if size_bytes < 1024:
                    file_info['file_size_formatted'] = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    file_info['file_size_formatted'] = f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    file_info['file_size_formatted'] = f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    file_info['file_size_formatted'] = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            else:
                file_info['file_size_formatted'] = "未知"

            # 格式化创建时间
            created_at = file_info.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        # 处理ISO格式字符串
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    elif isinstance(created_at, (int, float)):
                        # 处理Unix时间戳
                        dt = datetime.fromtimestamp(created_at)
                    else:
                        dt = created_at
                    file_info['created_at_formatted'] = dt.strftime('%Y-%m-%d %H:%M')
                except Exception as e:
                    logger.warning(f"时间格式化失败: {e}")
                    file_info['created_at_formatted'] = '未知时间'
            else:
                file_info['created_at_formatted'] = '未知时间'

        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        })

    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return jsonify({'error': '获取文件列表失败'}), 500

# Cookies管理相关API
@api_bp.route('/cookies/status')
def cookies_status():
    """检查cookies状态"""
    try:
        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        status = cookies_manager.get_status()

        return jsonify({
            'success': True,
            **status
        })

    except Exception as e:
        logger.error(f'检查cookies状态失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/test', methods=['GET', 'POST'])
def test_cookies():
    """测试cookies有效性"""
    try:
        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()

        # 处理POST请求中的平台参数
        platform = None
        if request.method == 'POST':
            data = request.get_json()
            if data:
                platform = data.get('platform')

        # 如果指定了平台，测试特定平台
        if platform:
            # 获取平台的cookies文件路径
            platform_files = cookies_manager.get_all_platform_cookies_files()
            cookies_file = platform_files.get(platform)

            if not cookies_file or not os.path.exists(cookies_file):
                result = {
                    'success': False,
                    'valid': False,
                    'error': f'{platform} 平台的cookies文件不存在',
                    'platform': platform
                }
            else:
                result = cookies_manager._test_platform_cookies(platform, cookies_file)
                result['platform'] = platform
        else:
            # 测试所有平台
            result = cookies_manager.test_cookies()

        return jsonify(result)

    except Exception as e:
        logger.error(f'测试cookies失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/import', methods=['POST'])
def import_cookies():
    """导入cookies"""
    try:
        data = request.get_json()
        cookies_content = data.get('cookies_content', '').strip()
        cookies_format = data.get('format', 'auto')
        import_mode = data.get('import_mode', 'standard')  # standard, preserve, raw
        platform = data.get('platform', 'youtube')

        if not cookies_content:
            return jsonify({
                'success': False,
                'error': '请提供cookies内容'
            }), 400

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()

        # 导入前自动备份现有cookies
        backup_result = None
        try:
            backup_name = f"auto_backup_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_result = cookies_manager.backup_cookies(backup_name)
            if backup_result['success']:
                logger.info(f"📦 导入前自动备份: {backup_name}")
        except Exception as e:
            logger.warning(f"自动备份失败，继续导入: {e}")

        # 根据导入模式选择不同的方法
        if import_mode == 'raw':
            result = cookies_manager.import_cookies_raw(cookies_content, platform)
            logger.info(f"✅ 用户使用原始模式导入了{platform}平台的cookies")
        elif import_mode == 'preserve':
            result = cookies_manager.import_cookies(cookies_content, cookies_format, preserve_format=True)
            logger.info(f"✅ 用户使用保持格式模式导入了cookies")
        else:
            result = cookies_manager.import_cookies(cookies_content, cookies_format)
            logger.info(f"✅ 用户使用标准模式导入了cookies")

        # 在结果中包含备份信息
        if backup_result and backup_result['success']:
            result['backup_info'] = {
                'backup_created': True,
                'backup_name': backup_result['backup_name'],
                'backup_message': f"已自动备份原有cookies到: {backup_result['backup_name']}"
            }
        else:
            result['backup_info'] = {
                'backup_created': False,
                'backup_message': '未创建备份（可能没有现有cookies文件）'
            }

        return jsonify(result)

    except Exception as e:
        logger.error(f'导入cookies失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/list')
def list_cookies():
    """列出当前导入的cookies文件"""
    try:
        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        cookies_files = cookies_manager.list_current_cookies()

        return jsonify({
            'success': True,
            'cookies_files': cookies_files
        })

    except Exception as e:
        logger.error(f'列出cookies文件失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/inspect', methods=['POST'])
def inspect_cookies():
    """检查cookies文件内容"""
    try:
        data = request.get_json()
        platform = data.get('platform')

        if not platform:
            return jsonify({
                'success': False,
                'error': '请指定平台'
            }), 400

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        result = cookies_manager.inspect_platform_cookies(platform)

        return jsonify(result)

    except Exception as e:
        logger.error(f'检查cookies失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/delete', methods=['POST'])
def delete_cookies():
    """删除指定平台的cookies文件"""
    try:
        data = request.get_json()
        platform = data.get('platform')

        if not platform:
            return jsonify({
                'success': False,
                'error': '请指定平台'
            }), 400

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        result = cookies_manager.delete_platform_cookies(platform)

        if result['success']:
            logger.info(f"✅ 用户删除了{platform}平台的cookies文件")

        return jsonify(result)

    except Exception as e:
        logger.error(f'删除cookies失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/clean', methods=['POST'])
def clean_cookies():
    """清理指定平台的过期cookies"""
    try:
        data = request.get_json()
        platform = data.get('platform')

        if not platform:
            return jsonify({
                'success': False,
                'error': '请指定平台'
            }), 400

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        result = cookies_manager.clean_platform_cookies(platform)

        if result['success']:
            logger.info(f"✅ 用户清理了{platform}平台的cookies文件")

        return jsonify(result)

    except Exception as e:
        logger.error(f'清理cookies失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/backup', methods=['POST'])
@login_required
def backup_cookies():
    """备份cookies"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.get_json() or {}
        backup_name = data.get('backup_name')

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        result = cookies_manager.backup_cookies(backup_name)

        if result['success']:
            logger.info(f"✅ 管理员备份了cookies: {result.get('backup_name')}")

        return jsonify(result)

    except Exception as e:
        logger.error(f'备份cookies失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/backups', methods=['GET'])
@login_required
def list_cookie_backups():
    """列出所有cookies备份"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        result = cookies_manager.list_backups()

        return jsonify(result)

    except Exception as e:
        logger.error(f'列出cookies备份失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/restore', methods=['POST'])
@login_required
def restore_cookies():
    """恢复cookies"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        data = request.get_json()
        backup_name = data.get('backup_name')

        if not backup_name:
            return jsonify({
                'success': False,
                'error': '请指定备份名称'
            }), 400

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        result = cookies_manager.restore_cookies(backup_name)

        if result['success']:
            logger.info(f"✅ 管理员恢复了cookies备份: {backup_name}")

        return jsonify(result)

    except Exception as e:
        logger.error(f'恢复cookies失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/cookies/backup/<backup_name>', methods=['DELETE'])
@login_required
def delete_cookie_backup(backup_name):
    """删除指定的cookies备份"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        from ..core.cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()
        result = cookies_manager.delete_backup(backup_name)

        if result['success']:
            logger.info(f"✅ 管理员删除了cookies备份: {backup_name}")

        return jsonify(result)

    except Exception as e:
        logger.error(f'删除cookies备份失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/telegram/test', methods=['POST'])
def test_telegram():
    """测试Telegram连接"""
    try:
        from ..core.telegram_notifier import get_telegram_notifier
        telegram_notifier = get_telegram_notifier()
        result = telegram_notifier.test_connection()
        return jsonify(result)

    except Exception as e:
        logger.error(f'测试Telegram连接失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/telegram/status')
def telegram_status():
    """获取Telegram状态"""
    try:
        from ..core.telegram_notifier import get_telegram_notifier
        telegram_notifier = get_telegram_notifier()

        return jsonify({
            'success': True,
            'enabled': telegram_notifier.is_enabled(),
            'bot_token_configured': bool(telegram_notifier.bot_token),
            'chat_id_configured': bool(telegram_notifier.chat_id)
        })

    except Exception as e:
        logger.error(f'获取Telegram状态失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/telegram/test-file', methods=['POST'])
def test_telegram_file():
    """测试Telegram文件发送"""
    try:
        data = request.get_json()
        test_file_path = data.get('file_path')

        if not test_file_path:
            return jsonify({
                'success': False,
                'error': '请提供测试文件路径'
            }), 400

        from ..core.telegram_notifier import get_telegram_notifier
        telegram_notifier = get_telegram_notifier()

        if not telegram_notifier.is_enabled():
            return jsonify({
                'success': False,
                'error': 'Telegram未配置'
            }), 400

        # 创建测试文件（如果不存在）
        import os
        from datetime import datetime
        if not os.path.exists(test_file_path):
            # 创建一个小的测试文件
            test_content = "这是一个Telegram文件推送测试文件\n测试时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_content)

        # 发送文件
        caption = "🧪 *Telegram文件推送测试*\n\n✅ 如果你收到这个文件，说明文件推送功能正常工作！"
        success = telegram_notifier.send_document(test_file_path, caption)

        # 清理测试文件
        if os.path.exists(test_file_path) and 'test' in test_file_path.lower():
            os.remove(test_file_path)

        if success:
            return jsonify({
                'success': True,
                'message': '测试文件发送成功！请检查Telegram是否收到文件。'
            })
        else:
            return jsonify({
                'success': False,
                'error': '文件发送失败，请检查日志获取详细信息'
            })

    except Exception as e:
        logger.error(f'测试Telegram文件发送失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/files/delete', methods=['POST'])
@login_required
def delete_file():
    """删除单个文件"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400

        filename = data.get('filename')
        file_path = data.get('file_path')

        if not filename:
            return jsonify({'error': '请指定文件名'}), 400

        # 如果没有提供file_path，尝试从下载目录构建
        if not file_path:
            download_folder = current_app.config['DOWNLOAD_FOLDER']
            file_path = os.path.join(download_folder, filename)

        # 安全检查：确保文件在下载目录内
        download_folder = os.path.abspath(current_app.config['DOWNLOAD_FOLDER'])
        file_path = os.path.abspath(file_path)

        if not file_path.startswith(download_folder):
            return jsonify({'error': '无效的文件路径'}), 400

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        # 删除文件
        os.remove(file_path)

        logger.info(f"✅ 用户删除了文件: {filename}")

        return jsonify({
            'success': True,
            'message': f'文件 "{filename}" 已删除'
        })

    except Exception as e:
        logger.error(f'删除文件失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_bp.route('/download-file/<filename>')
@login_required
def download_file(filename):
    """下载指定文件"""
    try:
        download_dir = os.environ.get('DOWNLOAD_FOLDER', '/app/downloads')
        file_path = os.path.join(download_dir, filename)

        # 安全检查：确保文件在下载目录内
        if not os.path.abspath(file_path).startswith(os.path.abspath(download_dir)):
            return jsonify({'error': '非法的文件路径'}), 400

        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return jsonify({'error': '下载失败'}), 500

@api_bp.route('/files/cleanup', methods=['POST'])
@login_required
def cleanup_files():
    """清理文件"""
    try:
        data = request.get_json() or {}
        cleanup_type = data.get('type', 'completed')  # completed, expired, all

        from ..file_cleaner import get_cleanup_manager
        cleanup_mgr = get_cleanup_manager()

        if not cleanup_mgr:
            return jsonify({'error': '清理管理器未初始化'}), 500

        cleaned_count = 0

        if cleanup_type == 'completed' or cleanup_type == 'all':
            # 清理所有下载文件
            cleaned_count = cleanup_mgr.cleanup_all_files()
        elif cleanup_type == 'expired':
            # 清理过期文件
            cleaned_count = cleanup_mgr._cleanup_expired_files()
        elif cleanup_type == 'temp':
            # 清理临时文件
            cleaned_count = cleanup_mgr._cleanup_temp_files()
        elif cleanup_type == 'pattern':
            # 按模式清理文件
            pattern = data.get('pattern', '*')
            keep_recent = data.get('keep_recent', 0)
            cleaned_count = cleanup_mgr.cleanup_files_by_pattern(pattern, keep_recent)
        else:
            return jsonify({'error': '无效的清理类型'}), 400

        return jsonify({
            'success': True,
            'message': f'清理完成，删除了 {cleaned_count} 个文件',
            'cleaned_count': cleaned_count
        })

    except Exception as e:
        logger.error(f"文件清理失败: {e}")
        return jsonify({'error': f'清理失败: {str(e)}'}), 500

@api_bp.route('/stream-file/<filename>')
@login_required
def stream_file(filename):
    """流式传输文件用于视频播放"""
    try:
        download_dir = os.environ.get('DOWNLOAD_FOLDER', '/app/downloads')
        file_path = os.path.join(download_dir, filename)

        # 安全检查：确保文件在下载目录内
        if not os.path.abspath(file_path).startswith(os.path.abspath(download_dir)):
            return jsonify({'error': '非法的文件路径'}), 400

        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        # 检查是否为视频文件
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension not in video_extensions:
            return jsonify({'error': '不支持的视频格式'}), 400

        # 获取MIME类型
        mime_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.ogv': 'video/ogg',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.mkv': 'video/x-matroska',
            '.m4v': 'video/mp4',
            '.3gp': 'video/3gpp'
        }

        mimetype = mime_types.get(file_extension, 'video/mp4')

        # 流式传输文件，不作为附件下载
        return send_file(
            file_path,
            as_attachment=False,  # 不作为下载
            mimetype=mimetype,
            conditional=True  # 支持范围请求，用于视频播放
        )

    except Exception as e:
        logger.error(f"流式传输文件失败: {e}")
        return jsonify({'error': '流式传输失败'}), 500

# Admin API routes
@api_bp.route('/admin/cleanup', methods=['POST'])
@login_required
def admin_cleanup():
    """手动清理文件"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        from ..file_cleaner import get_cleanup_manager
        cleanup_mgr = get_cleanup_manager()
        if not cleanup_mgr:
            return jsonify({'error': '清理管理器未初始化'}), 500

        # 检查是否强制清理
        data = request.get_json() or {}
        force_cleanup = data.get('force', False)

        if force_cleanup:
            # 强制清理：删除所有文件（除了最近1个）
            import os
            download_dir = os.environ.get('DOWNLOAD_FOLDER', '/app/downloads')
            cleaned_files = 0

            if os.path.exists(download_dir):
                files = []
                for filename in os.listdir(download_dir):
                    file_path = os.path.join(download_dir, filename)
                    if os.path.isfile(file_path):
                        files.append((file_path, os.path.getmtime(file_path)))

                # 按时间排序，保留最新的1个文件
                files.sort(key=lambda x: x[1], reverse=True)

                for i, (file_path, _) in enumerate(files):
                    if i >= 1:  # 保留最新的1个文件
                        try:
                            os.remove(file_path)
                            cleaned_files += 1
                            logger.info(f"强制删除文件: {os.path.basename(file_path)}")
                        except Exception as e:
                            logger.error(f"删除文件失败 {file_path}: {e}")
        else:
            # 正常清理
            cleaned_files = cleanup_mgr.cleanup_files()

        # 获取更新后的存储信息
        storage_info = cleanup_mgr.get_storage_info()

        return jsonify({
            'success': True,
            'message': f'清理完成{"（强制模式）" if force_cleanup else ""}',
            'cleaned_files': cleaned_files,
            'storage_info': storage_info,
            'force_cleanup': force_cleanup
        })

    except Exception as e:
        logger.error(f"手动清理失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/storage-info', methods=['GET'])
@login_required
def admin_storage_info():
    """获取存储信息"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        from ..file_cleaner import get_cleanup_manager
        cleanup_mgr = get_cleanup_manager()
        if not cleanup_mgr:
            return jsonify({'error': '清理管理器未初始化'}), 500

        storage_info = cleanup_mgr.get_storage_info()

        return jsonify({
            'success': True,
            'storage_info': storage_info
        })

    except Exception as e:
        logger.error(f"获取存储信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/cleanup-config', methods=['GET', 'POST'])
@login_required
def admin_cleanup_config():
    """获取或更新清理配置"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        from ..file_cleaner import get_cleanup_manager
        cleanup_mgr = get_cleanup_manager()
        if not cleanup_mgr:
            return jsonify({'error': '清理管理器未初始化'}), 500

        if request.method == 'GET':
            config = cleanup_mgr.get_config()
            return jsonify(config)  # 直接返回配置，不包装在success中
        else:
            # POST - 更新配置
            data = request.get_json()
            if not data:
                return jsonify({'error': '无效的配置数据'}), 400

            cleanup_mgr.update_config(data)

            return jsonify({
                'success': True,
                'message': '配置已更新'
            })

    except Exception as e:
        logger.error(f"清理配置操作失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/version', methods=['GET'])
@login_required
def admin_version():
    """获取版本信息"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        import subprocess
        import sys
        import os

        # 获取 yt-dlp 版本
        try:
            result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'],
                                  capture_output=True, text=True, timeout=10)
            ytdlp_version = result.stdout.strip() if result.returncode == 0 else '未知'
        except Exception:
            ytdlp_version = '未知'

        # 获取 Python 版本
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # 获取应用版本（可以从环境变量或配置文件读取）
        app_version = os.environ.get('APP_VERSION', '1.0.0')

        return jsonify({
            'success': True,
            'version_info': {
                'app_version': app_version,
                'ytdlp_version': ytdlp_version,
                'python_version': python_version,
                'last_updated': '未知'  # 可以后续添加实际的更新时间
            }
        })

    except Exception as e:
        logger.error(f"获取版本信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/admin/update-check', methods=['GET'])
@login_required
def admin_update_check():
    """检查yt-dlp更新"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        import subprocess
        import sys
        import re

        # 获取当前yt-dlp版本
        try:
            result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'],
                                  capture_output=True, text=True, timeout=10)
            current_version = result.stdout.strip() if result.returncode == 0 else '未知'
        except Exception:
            current_version = '未知'

        # 改进的更新检查逻辑
        try:
            logger.info("检查yt-dlp更新...")

            # 方法1: 通过pip检查最新版本
            latest_version = current_version
            update_available = False

            try:
                # 使用pip show检查当前安装的版本
                pip_show_result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'yt-dlp'],
                                                capture_output=True, text=True, timeout=15)

                if pip_show_result.returncode == 0:
                    # 解析当前版本
                    for line in pip_show_result.stdout.split('\n'):
                        if line.startswith('Version:'):
                            current_pip_version = line.split(':', 1)[1].strip()
                            if current_pip_version != current_version:
                                current_version = current_pip_version
                            break

                # 检查PyPI上的最新版本
                pip_search_result = subprocess.run([sys.executable, '-m', 'pip', 'index', 'versions', 'yt-dlp'],
                                                 capture_output=True, text=True, timeout=20)

                if pip_search_result.returncode == 0:
                    # 解析最新版本
                    output = pip_search_result.stdout
                    # 查找 "Available versions:" 后的第一个版本
                    if 'Available versions:' in output:
                        versions_line = output.split('Available versions:')[1].split('\n')[0]
                        versions = [v.strip() for v in versions_line.split(',') if v.strip()]
                        if versions:
                            latest_version = versions[0]
                            update_available = latest_version != current_version

            except Exception as pip_error:
                logger.warning(f"pip检查失败: {pip_error}")

            # 方法2: 如果pip方法失败，使用yt-dlp自身检查
            if latest_version == current_version:
                try:
                    # 使用yt-dlp的内置更新检查
                    update_check_result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'],
                                                       capture_output=True, text=True, timeout=10)

                    if update_check_result.returncode == 0:
                        # 简单假设总是有更新可用（保守方法）
                        update_available = True
                        message = '建议检查yt-dlp更新'
                    else:
                        message = 'yt-dlp版本检查完成'

                except Exception:
                    message = 'yt-dlp版本检查完成'

            # 设置最终消息
            if update_available:
                if latest_version != current_version:
                    message = f'发现yt-dlp新版本: {latest_version} (当前: {current_version})'
                else:
                    message = '可能有yt-dlp新版本可用'
            else:
                message = 'yt-dlp已是最新版本'

        except Exception as e:
            logger.warning(f"检查yt-dlp更新失败: {e}")
            latest_version = current_version
            update_available = False
            message = 'yt-dlp版本检查失败，建议手动更新'

        return jsonify({
            'success': True,
            'update_available': update_available,
            'current_version': current_version,
            'latest_version': latest_version,
            'message': message,
            'component': 'yt-dlp'
        })

    except Exception as e:
        logger.error(f"检查yt-dlp更新失败: {e}")
        return jsonify({'error': str(e)}), 500

def update_ytdlp_to_project_dir():
    """直接下载并覆盖/app/yt_dlp目录"""
    import tempfile
    import shutil
    import zipfile
    import requests
    from pathlib import Path

    try:
        logger.info("🔄 开始下载最新yt-dlp源码...")

        # GitHub API获取最新release
        api_url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        response = requests.get(api_url, timeout=30)

        if response.status_code != 200:
            return {'success': False, 'error': f'获取release信息失败: {response.status_code}'}

        release_data = response.json()
        latest_version = release_data['tag_name']

        # 查找源码下载链接
        zipball_url = None
        for asset in release_data.get('assets', []):
            if asset['name'].endswith('.tar.gz') and 'source' not in asset['name'].lower():
                # 使用zipball_url更简单
                zipball_url = release_data['zipball_url']
                break

        if not zipball_url:
            zipball_url = release_data['zipball_url']

        logger.info(f"📥 下载版本 {latest_version} 从: {zipball_url}")

        # 下载源码
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_file = temp_path / "yt-dlp.zip"

            # 下载文件
            download_response = requests.get(zipball_url, timeout=120, stream=True)
            download_response.raise_for_status()

            with open(zip_file, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info("✅ 下载完成，开始解压...")

            # 解压文件
            extract_dir = temp_path / "extracted"
            extract_dir.mkdir()

            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 查找yt_dlp目录
            ytdlp_source_dir = None
            for item in extract_dir.iterdir():
                if item.is_dir():
                    ytdlp_candidate = item / "yt_dlp"
                    if ytdlp_candidate.exists() and (ytdlp_candidate / "__init__.py").exists():
                        ytdlp_source_dir = ytdlp_candidate
                        break

            if not ytdlp_source_dir:
                return {'success': False, 'error': '在下载的源码中未找到yt_dlp目录'}

            logger.info(f"📂 找到yt_dlp源码目录: {ytdlp_source_dir}")

            # 备份现有目录
            app_ytdlp_dir = Path("/app/yt_dlp")
            backup_dir = None

            if app_ytdlp_dir.exists():
                backup_dir = Path(f"/app/yt_dlp_backup_{int(__import__('time').time())}")
                logger.info(f"💾 备份现有目录到: {backup_dir}")
                shutil.move(str(app_ytdlp_dir), str(backup_dir))

            # 复制新版本
            logger.info(f"📋 复制新版本到: {app_ytdlp_dir}")
            shutil.copytree(str(ytdlp_source_dir), str(app_ytdlp_dir))

            # 设置权限
            os.system(f"chmod -R 755 {app_ytdlp_dir}")

            logger.info("✅ yt-dlp目录更新完成")

            return {
                'success': True,
                'version': latest_version,
                'backup_dir': str(backup_dir) if backup_dir else None,
                'method': 'direct_download'
            }

    except Exception as e:
        logger.error(f"直接更新失败: {e}")
        return {'success': False, 'error': str(e)}

@api_bp.route('/admin/update', methods=['POST'])
@login_required
def admin_update():
    """更新yt-dlp"""
    try:
        # 检查管理员权限
        if not current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        import subprocess
        import sys

        # 执行yt-dlp更新
        try:
            logger.info("开始更新yt-dlp...")

            # 先检查pip是否可用
            pip_check = subprocess.run([sys.executable, '-m', 'pip', '--version'],
                                     capture_output=True, text=True, timeout=10)
            if pip_check.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': 'pip不可用，无法执行更新'
                }), 500

            # 获取更新前的版本和项目文件状态
            old_version_result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'],
                                              capture_output=True, text=True, timeout=10)
            old_version = old_version_result.stdout.strip() if old_version_result.returncode == 0 else '未知'

            # 记录关键项目文件的修改时间（用于验证文件未被修改）
            import os
            project_files = [
                '/app/webapp/app.py',
                '/app/webapp/routes/api.py',
                '/app/webapp/templates/admin.html'
            ]

            file_times_before = {}
            for file_path in project_files:
                if os.path.exists(file_path):
                    file_times_before[file_path] = os.path.getmtime(file_path)

            # 检查当前yt-dlp来源
            ytdlp_source = "unknown"
            try:
                import yt_dlp
                ytdlp_location = yt_dlp.__file__
                if '/app/yt-dlp-source/' in ytdlp_location:
                    ytdlp_source = "build-time"
                elif '/app/yt-dlp-runtime/' in ytdlp_location:
                    ytdlp_source = "runtime"
                elif 'site-packages' in ytdlp_location:
                    ytdlp_source = "pip"
                logger.info(f"当前yt-dlp来源: {ytdlp_source} ({ytdlp_location})")
            except Exception as e:
                logger.warning(f"无法确定yt-dlp来源: {e}")

            # 执行更新 - 直接覆盖项目目录
            logger.info(f"当前版本: {old_version}，开始更新yt-dlp（直接覆盖项目目录）...")

            # 新策略：直接下载并覆盖/app/yt_dlp目录
            result = update_ytdlp_to_project_dir()

            if not result['success']:
                # 如果直接更新失败，回退到pip方式
                logger.warning("直接更新失败，回退到pip方式...")
                pip_cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade', '--force-reinstall', '--no-cache-dir']

                if os.getuid() == 0:
                    pip_cmd.append('--break-system-packages')

                pip_cmd.append('yt-dlp')
                pip_result = subprocess.run(pip_cmd, capture_output=True, text=True, timeout=120)

                if pip_result.returncode != 0:
                    error_msg = pip_result.stderr or pip_result.stdout or '更新失败'
                    logger.error(f"pip更新也失败: {error_msg}")
                    return jsonify({
                        'success': False,
                        'error': f'更新失败: {error_msg}',
                        'details': result.get('error', '')
                    }), 500

            # 检查更新结果
            if result['success']:
                # 获取更新后的版本
                version_result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'],
                                              capture_output=True, text=True, timeout=10)
                new_version = version_result.stdout.strip() if version_result.returncode == 0 else '未知'

                # 验证项目文件未被修改
                file_verification = []
                for file_path in project_files:
                    if os.path.exists(file_path):
                        time_after = os.path.getmtime(file_path)
                        time_before = file_times_before.get(file_path, 0)
                        if time_after == time_before:
                            file_verification.append(f"✅ {os.path.basename(file_path)}: 未修改")
                        else:
                            file_verification.append(f"⚠️ {os.path.basename(file_path)}: 时间变化")

                # 检查更新后的yt-dlp来源
                new_ytdlp_source = "unknown"
                try:
                    # 重新导入以获取最新信息
                    import importlib
                    import yt_dlp
                    importlib.reload(yt_dlp)
                    new_ytdlp_location = yt_dlp.__file__
                    if '/app/yt-dlp-source/' in new_ytdlp_location:
                        new_ytdlp_source = "build-time"
                    elif '/app/yt-dlp-runtime/' in new_ytdlp_location:
                        new_ytdlp_source = "runtime"
                    elif 'site-packages' in new_ytdlp_location:
                        new_ytdlp_source = "pip"
                except Exception:
                    pass

                # 检查是否真的更新了
                update_method = result.get('method', 'unknown')
                backup_info = result.get('backup_dir', None)

                if new_version != old_version or result.get('version'):
                    # 使用result中的版本信息（如果有的话）
                    actual_new_version = result.get('version', new_version)
                    logger.info(f"yt-dlp更新成功: {old_version} → {actual_new_version}")
                    logger.info("项目文件验证: " + ", ".join(file_verification))

                    update_note = f'✅ yt-dlp已直接更新到项目目录'
                    if update_method == 'direct_download':
                        update_note += f'\n📂 直接覆盖了 /app/yt_dlp 目录'
                        if backup_info:
                            update_note += f'\n💾 原目录已备份到: {backup_info}'
                        update_note += f'\n🎯 无需重启，立即生效！'

                    return jsonify({
                        'success': True,
                        'message': f'yt-dlp更新成功！{old_version} → {actual_new_version}',
                        'old_version': old_version,
                        'new_version': actual_new_version,
                        'updated': True,
                        'file_verification': file_verification,
                        'ytdlp_source': 'project_directory',
                        'update_method': update_method,
                        'backup_dir': backup_info,
                        'safety_note': '✅ 直接更新项目目录，立即生效',
                        'update_note': update_note
                    })
                else:
                    logger.info(f"yt-dlp已是最新版本: {new_version}")
                    return jsonify({
                        'success': True,
                        'message': f'yt-dlp已是最新版本: {new_version}',
                        'old_version': old_version,
                        'new_version': new_version,
                        'updated': False,
                        'file_verification': file_verification,
                        'ytdlp_source': ytdlp_source,
                        'safety_note': '✅ 项目文件完全安全'
                    })
            else:
                error_msg = result.stderr or result.stdout or '更新失败'
                logger.error(f"yt-dlp更新失败: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': f'yt-dlp更新失败: {error_msg}',
                    'details': {
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                }), 500

        except subprocess.TimeoutExpired:
            logger.error("yt-dlp更新超时")
            return jsonify({
                'success': False,
                'error': 'yt-dlp更新超时（120秒），请检查网络连接后重试'
            }), 500

    except Exception as e:
        logger.error(f"yt-dlp更新失败: {e}")
        return jsonify({'error': str(e)}), 500

# 测试代码已删除
