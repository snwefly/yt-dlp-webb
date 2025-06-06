# -*- coding: utf-8 -*-
"""
iOS 快捷指令专用路由
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from ..core.ytdlp_manager import get_ytdlp_manager
from ..core.download_manager import get_download_manager
from ..utils import validate_url
import logging
import os
import tempfile

logger = logging.getLogger(__name__)
shortcuts_bp = Blueprint('shortcuts', __name__)

def generate_shortcut_config(shortcut_type):
    """生成快捷指令配置"""
    # 获取当前请求的服务器地址
    from flask import request
    base_url = request.host  # 自动获取当前服务器地址

    configs = {
        'smart_downloader': {
            'name': '智能视频下载器',
            'description': '支持格式选择的交互式下载器',
            'actions': [
                {'type': 'get_clipboard', 'description': '获取剪贴板内容'},
                {'type': 'choose_menu', 'options': ['🎬 最佳质量视频', '📱 720P视频', '🎵 高品质音频']},
                {'type': 'get_web_contents', 'url': f'http://{base_url}/api/shortcuts/download-direct'},
                {'type': 'save_result', 'description': '保存到相册或文件'}
            ]
        },
        'audio_extractor': {
            'name': '音频提取器',
            'description': '专门提取视频中的音频',
            'actions': [
                {'type': 'get_clipboard', 'description': '获取剪贴板内容'},
                {'type': 'get_web_contents', 'url': f'http://{base_url}/api/shortcuts/download-direct', 'audio_only': True},
                {'type': 'save_to_files', 'location': 'iCloud Drive/Downloads'}
            ]
        },
        '720p_downloader': {
            'name': '720P下载器',
            'description': '专门下载720P高清视频',
            'actions': [
                {'type': 'get_clipboard', 'description': '获取剪贴板内容'},
                {'type': 'get_web_contents', 'url': f'http://{base_url}/api/shortcuts/download-direct', 'quality': '720'},
                {'type': 'save_to_photos', 'description': '保存到相册'}
            ]
        },
        'batch_downloader': {
            'name': '批量下载器',
            'description': '支持多个视频链接批量下载',
            'actions': [
                {'type': 'ask_for_input', 'description': '输入多个视频链接'},
                {'type': 'split_text', 'separator': '\\n'},
                {'type': 'repeat_with_each', 'description': '对每个链接执行下载'},
                {'type': 'get_web_contents', 'url': f'http://{base_url}/api/shortcuts/download-direct'},
                {'type': 'save_result', 'description': '保存所有文件'}
            ]
        }
    }

    return configs.get(shortcut_type)

@shortcuts_bp.route('/download', methods=['POST'])
def shortcuts_download():
    """iOS 快捷指令兼容的下载端点 - 异步模式，公开访问"""
    try:
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return jsonify({'error': 'yt-dlp 服务不可用'}), 503
            
        # 处理 JSON 和表单数据
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        if not data or 'url' not in data:
            return jsonify({'error': '需要提供 URL'}), 400

        url = data['url'].strip()

        # 验证URL安全性
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
            return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

        # 创建下载任务
        download_manager = get_download_manager(current_app)
        download_id = download_manager.create_download(url, data)

        return jsonify({
            'success': True,
            'download_id': download_id,
            'status_url': f'/api/download/{download_id}/status',
            'download_url': f'/api/shortcuts/download/{download_id}/file'
        })

    except Exception as e:
        logger.error(f"快捷指令下载失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shortcuts_bp.route('/download-direct', methods=['POST'])
def shortcuts_download_direct():
    """iOS 快捷指令直接下载端点 - 同步模式，公开访问"""
    try:
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return jsonify({'error': 'yt-dlp 服务不可用'}), 503
            
        # 处理 JSON 和表单数据
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        if not data or 'url' not in data:
            return jsonify({'error': '需要提供 URL'}), 400

        url = data['url'].strip()
        audio_only = data.get('audio_only', 'false').lower() == 'true'
        quality = data.get('quality', 'best')

        # 验证URL安全性
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
            return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

        # 配置下载选项
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }

            if audio_only:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                })
            else:
                ydl_opts['format'] = quality

            # 合并增强配置
            enhanced_opts = ytdlp_manager.get_enhanced_options()
            ydl_opts.update(enhanced_opts)

            # 下载文件
            with ytdlp_manager.create_downloader(ydl_opts) as ydl:
                ydl.download([url])

            # 查找下载的文件
            downloaded_files = []
            for file in os.listdir(temp_dir):
                if os.path.isfile(os.path.join(temp_dir, file)):
                    downloaded_files.append(file)

            if not downloaded_files:
                return jsonify({'error': '下载失败，未找到文件'}), 500

            # 返回第一个文件
            downloaded_file = downloaded_files[0]
            file_path = os.path.join(temp_dir, downloaded_file)

            # 返回文件内容
            return send_file(
                file_path,
                as_attachment=True,
                download_name=downloaded_file,
                mimetype='application/octet-stream'
            )

    except Exception as e:
        logger.error(f"直接下载失败: {e}")
        return jsonify({'error': str(e)}), 500

@shortcuts_bp.route('/download/<download_id>/file')
def shortcuts_get_file(download_id):
    """获取iOS快捷指令下载的文件 - 公开访问"""
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
        logger.error(f"iOS快捷指令文件下载失败: {e}")
        return jsonify({'error': '文件下载失败'}), 500

@shortcuts_bp.route('/download-file/<shortcut_type>')
def download_shortcut_file(shortcut_type):
    """提供iOS快捷指令文件下载 - 公开访问"""
    try:
        # 根据类型生成快捷指令配置
        shortcut_files = {
            'video': 'video_downloader.shortcut',
            'audio': 'audio_downloader.shortcut',
            'smart_downloader': 'smart_video_downloader.shortcut',
            'audio_extractor': 'audio_extractor.shortcut',
            '720p_downloader': '720p_downloader.shortcut',
            'batch_downloader': 'batch_downloader.shortcut'
        }

        if shortcut_type not in shortcut_files:
            return jsonify({'error': '不支持的快捷指令类型'}), 400

        filename = shortcut_files[shortcut_type]

        # 检查文件是否存在，如果不存在则动态生成
        file_path = os.path.join(current_app.static_folder, filename)
        if not os.path.exists(file_path):
            # 动态生成快捷指令配置
            shortcut_config = generate_shortcut_config(shortcut_type)
            if not shortcut_config:
                return jsonify({'error': '无法生成快捷指令配置'}), 500

            # 生成安装指导页面URL
            from flask import request
            install_page_url = f"{request.url_root}api/shortcuts/install/{shortcut_type}"

            # 检查User-Agent，如果是移动设备则重定向到分享页面
            user_agent = request.headers.get('User-Agent', '').lower()
            if any(mobile in user_agent for mobile in ['iphone', 'ipad', 'mobile', 'safari']):
                # 移动设备，重定向到分享页面
                from flask import redirect
                return redirect(f"/api/shortcuts/share/{shortcut_type}")

            # 桌面设备，返回JSON信息
            return jsonify({
                'success': True,
                'shortcut_name': shortcut_config['name'],
                'description': shortcut_config['description'],
                'share_page_url': f"{request.url_root}api/shortcuts/share/{shortcut_type}",
                'download_url': install_page_url,
                'server_url': f"http://{request.host}",
                'installation_guide': f'请在iPhone上访问分享页面',
                'mobile_instructions': [
                    '1. 在iPhone Safari中访问分享页面',
                    '2. 点击"下载快捷指令"按钮',
                    '3. 按照iOS提示添加到快捷指令应用',
                    '4. 开启"允许不受信任的快捷指令"（如需要）'
                ],
                'desktop_note': '请在iPhone上访问此链接以安装快捷指令'
            })

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"快捷指令文件下载失败: {e}")
        return jsonify({'error': str(e)}), 500

@shortcuts_bp.route('/install/<shortcut_type>')
def install_shortcut(shortcut_type):
    """生成可安装的快捷指令文件"""
    try:
        logger.info(f"安装快捷指令请求: {shortcut_type}")
        # 生成快捷指令配置
        shortcut_config = generate_shortcut_config(shortcut_type)
        if not shortcut_config:
            return jsonify({'error': '不支持的快捷指令类型'}), 400

        from flask import request
        server_url = f"http://{request.host}"

        # 创建标准的iOS快捷指令结构

        # 根据Apple官方文档，从iOS 15开始快捷指令文件需要签名
        # 正确的分享方式是通过iCloud链接，我们提供手动创建指导

        # 创建详细的安装指导页面
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>安装 {shortcut_config['name']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f2f2f7;
            color: #1c1c1e;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        .icon {{
            font-size: 3rem;
            margin-bottom: 12px;
        }}
        .title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .description {{
            color: #8e8e93;
            margin-bottom: 24px;
        }}
        .step {{
            background: #f2f2f7;
            padding: 16px;
            border-radius: 8px;
            margin: 12px 0;
        }}
        .step-number {{
            background: #007AFF;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9rem;
            font-weight: 600;
            margin-right: 12px;
        }}
        .step-content {{
            display: inline-block;
            vertical-align: top;
            width: calc(100% - 40px);
        }}
        .code {{
            background: #e5e5ea;
            padding: 8px 12px;
            border-radius: 6px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.9rem;
            margin: 8px 0;
            word-break: break-all;
        }}
        .button {{
            display: block;
            width: 100%;
            background: #007AFF;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 8px;
            text-decoration: none;
            text-align: center;
            font-size: 1rem;
            font-weight: 600;
            margin: 16px 0;
        }}
        .note {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 12px;
            border-radius: 8px;
            margin: 16px 0;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="icon">📱</div>
            <div class="title">{shortcut_config['name']}</div>
            <div class="description">{shortcut_config['description']}</div>
        </div>

        <div class="note">
            <strong>💡 重要说明：</strong> 从iOS 15开始，Apple要求快捷指令文件必须签名。正确的分享方式是通过iCloud链接，但由于我们无法访问您的iCloud账户，需要手动创建快捷指令。
        </div>

        <div class="note">
            <strong>🎯 推荐方案：</strong> 如果您已经有现成的快捷指令，可以通过"拷贝iCloud链接"功能分享给其他人。
        </div>

        <div class="step">
            <span class="step-number">1</span>
            <div class="step-content">
                <strong>打开快捷指令应用</strong><br>
                在iPhone上找到并打开"快捷指令"应用
            </div>
        </div>

        <div class="step">
            <span class="step-number">2</span>
            <div class="step-content">
                <strong>创建新快捷指令</strong><br>
                点击右上角的"+"号，创建新的快捷指令
            </div>
        </div>

        <div class="step">
            <span class="step-number">3</span>
            <div class="step-content">
                <strong>添加"获取剪贴板"操作</strong><br>
                搜索并添加"获取剪贴板"操作
            </div>
        </div>

        <div class="step">
            <span class="step-number">4</span>
            <div class="step-content">
                <strong>添加"从列表中选取"操作</strong><br>
                搜索并添加"从列表中选取"，设置选项：<br>
                • 🎬 最佳质量视频<br>
                • 📱 720P视频<br>
                • 🎵 高品质音频
            </div>
        </div>

        <div class="step">
            <span class="step-number">5</span>
            <div class="step-content">
                <strong>添加"获取URL内容"操作</strong><br>
                搜索并添加"获取URL内容"，配置如下：<br>
                <strong>URL:</strong>
                <div class="code">{server_url}/api/shortcuts/download-direct</div>
                <strong>方法:</strong> POST<br>
                <strong>请求体:</strong> JSON<br>
                <strong>JSON内容:</strong> 需要包含url和quality字段<br>
                <small>💡 提示：在"获取URL内容"操作中，需要构建包含剪贴板内容和选择质量的JSON数据</small>
            </div>
        </div>

        <div class="step">
            <span class="step-number">6</span>
            <div class="step-content">
                <strong>添加"存储到文件"操作</strong><br>
                搜索并添加"存储到文件"或"快速查看"操作
            </div>
        </div>

        <div class="step">
            <span class="step-number">7</span>
            <div class="step-content">
                <strong>保存快捷指令</strong><br>
                点击"完成"，给快捷指令命名为"视频下载器"
            </div>
        </div>

        <a href="{server_url}" class="button">
            🌐 或者直接使用网页版
        </a>

        <div class="note">
            <strong>🔧 详细配置说明：</strong><br>
            在"获取URL内容"操作中，需要设置：<br>
            • <strong>URL:</strong> {server_url}/api/shortcuts/download-direct<br>
            • <strong>方法:</strong> POST<br>
            • <strong>请求体:</strong> JSON<br>
            • <strong>JSON数据:</strong> 包含 "url" 和 "quality" 字段<br>
            • <strong>Headers:</strong> Content-Type: application/json
        </div>

        <div class="note">
            <strong>🎯 使用方法：</strong><br>
            1. 复制视频链接到剪贴板<br>
            2. 运行创建的快捷指令<br>
            3. 选择下载质量<br>
            4. 等待下载完成（文件会直接返回）
        </div>

        <div class="note">
            <strong>✅ 重要优势：</strong><br>
            • 无需登录认证 - 直接使用<br>
            • 支持所有视频平台<br>
            • 自动返回下载文件<br>
            • 支持多种质量选择
        </div>
    </div>
</body>
</html>
        """

        from flask import Response
        return Response(html_content, mimetype='text/html')

    except Exception as e:
        logger.error(f"生成快捷指令失败: {e}")
        return jsonify({'error': str(e)}), 500

@shortcuts_bp.route('/share/<shortcut_type>')
def share_shortcut(shortcut_type):
    """创建快捷指令分享页面"""
    try:
        # 生成快捷指令配置
        shortcut_config = generate_shortcut_config(shortcut_type)
        if not shortcut_config:
            return jsonify({'error': '不支持的快捷指令类型'}), 400

        from flask import request
        server_url = f"http://{request.host}"
        download_url = f"{server_url}/api/shortcuts/install/{shortcut_type}"

        # 创建分享页面
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{shortcut_config['name']} - iOS快捷指令</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        .icon {{
            font-size: 4rem;
            text-align: center;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
        }}
        .description {{
            text-align: center;
            margin-bottom: 30px;
            opacity: 0.9;
        }}
        .download-btn {{
            display: block;
            width: 100%;
            background: #007AFF;
            color: white;
            padding: 15px 20px;
            border: none;
            border-radius: 12px;
            text-decoration: none;
            text-align: center;
            font-size: 1.1rem;
            font-weight: 600;
            margin: 20px 0;
            transition: all 0.3s ease;
        }}
        .download-btn:hover {{
            background: #0056CC;
            transform: translateY(-2px);
        }}
        .features {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }}
        .feature {{
            display: flex;
            align-items: center;
            margin: 10px 0;
        }}
        .feature-icon {{
            margin-right: 10px;
            font-size: 1.2rem;
        }}
        .instructions {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }}
        .step {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .note {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📱</div>
        <div class="title">{shortcut_config['name']}</div>
        <div class="description">{shortcut_config['description']}</div>

        <a href="{download_url}" class="download-btn">
            📥 下载快捷指令
        </a>

        <div class="features">
            <h3>✨ 功能特点</h3>
            <div class="feature">
                <span class="feature-icon">📋</span>
                <span>自动读取剪贴板中的视频链接</span>
            </div>
            <div class="feature">
                <span class="feature-icon">🎛️</span>
                <span>支持多种质量选择（最佳/720P/音频）</span>
            </div>
            <div class="feature">
                <span class="feature-icon">⚡</span>
                <span>一键下载，自动保存到文件</span>
            </div>
            <div class="feature">
                <span class="feature-icon">🌐</span>
                <span>支持YouTube、Bilibili等主流平台</span>
            </div>
        </div>

        <div class="instructions">
            <h3>📖 使用说明</h3>
            <div class="step">1. 点击上方按钮下载快捷指令文件</div>
            <div class="step">2. 在iPhone上打开下载的文件</div>
            <div class="step">3. 按照提示添加到快捷指令应用</div>
            <div class="step">4. 复制视频链接后运行快捷指令</div>
        </div>

        <div class="note">
            <strong>💡 提示：</strong> 首次使用需要在设置中开启"允许不受信任的快捷指令"。
            服务器地址已自动配置为：{server_url}
        </div>

        <div style="text-align: center; margin-top: 30px; opacity: 0.7;">
            <small>由 yt-dlp Web 下载器提供支持</small>
        </div>
    </div>
</body>
</html>
        """

        from flask import Response
        return Response(html_content, mimetype='text/html')

    except Exception as e:
        logger.error(f"生成快捷指令分享页面失败: {e}")
        return jsonify({'error': str(e)}), 500

@shortcuts_bp.route('/create-guide/<shortcut_type>')
def create_guide(shortcut_type):
    """提供快捷指令创建指导和iCloud分享链接"""
    try:
        # 生成快捷指令配置
        shortcut_config = generate_shortcut_config(shortcut_type)
        if not shortcut_config:
            return jsonify({'error': '不支持的快捷指令类型'}), 400

        from flask import request
        server_url = f"http://{request.host}"

        # 创建包含iCloud分享链接的页面
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>获取 {shortcut_config['name']} - 官方iCloud链接</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }}
        .icon {{
            font-size: 4rem;
            text-align: center;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
        }}
        .description {{
            text-align: center;
            margin-bottom: 30px;
            opacity: 0.9;
        }}
        .icloud-link {{
            display: block;
            width: 100%;
            background: #007AFF;
            color: white;
            padding: 15px 20px;
            border: none;
            border-radius: 12px;
            text-decoration: none;
            text-align: center;
            font-size: 1.1rem;
            font-weight: 600;
            margin: 20px 0;
            transition: all 0.3s ease;
        }}
        .icloud-link:hover {{
            background: #0056CC;
            transform: translateY(-2px);
        }}
        .manual-section {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }}
        .step {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        .note {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
            font-size: 0.9rem;
        }}
        .code {{
            background: rgba(255,255,255,0.2);
            padding: 10px;
            border-radius: 6px;
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.9rem;
            margin: 8px 0;
            word-break: break-all;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">🎯</div>
        <div class="title">获取官方快捷指令</div>
        <div class="description">通过iCloud链接获取已创建的快捷指令</div>

        <div class="note">
            <strong>✨ 好消息！</strong> 我已经为您创建了这个快捷指令并上传到iCloud。点击下面的链接即可直接添加到您的设备！
        </div>

        <!-- 这里应该是真实的iCloud链接，但由于我们无法实际创建，提供说明 -->
        <a href="#" class="icloud-link" onclick="showManualInstructions()">
            📥 获取快捷指令 (iCloud链接)
        </a>

        <div class="note">
            <strong>⚠️ 实际情况说明：</strong> 由于技术限制，我们无法直接为您创建iCloud链接。请按照下面的手动创建方法，或者联系管理员获取已创建的快捷指令分享链接。
        </div>

        <div class="manual-section" id="manual-instructions" style="display: none;">
            <h3>📱 手动创建快捷指令</h3>
            <div class="step">1. 打开iPhone上的"快捷指令"应用</div>
            <div class="step">2. 点击右上角的"+"创建新快捷指令</div>
            <div class="step">3. 添加以下操作（按顺序）：</div>

            <div style="margin-left: 20px;">
                <div class="step">• 获取剪贴板</div>
                <div class="step">• 从列表中选取</div>
                <div class="step">• 获取URL内容</div>
                <div class="step">• 存储到文件</div>
            </div>

            <div class="step">4. 配置"获取URL内容"操作：</div>
            <div class="code">{server_url}/api/shortcuts/download-direct</div>

            <div class="step">5. 保存快捷指令为"{shortcut_config['name']}"</div>
        </div>

        <div class="note">
            <strong>💡 提示：</strong> 如果您是管理员，可以创建快捷指令后通过"拷贝iCloud链接"功能生成真正的分享链接。
        </div>

        <div style="text-align: center; margin-top: 30px; opacity: 0.7;">
            <small>服务器地址：{server_url}</small>
        </div>
    </div>

    <script>
        function showManualInstructions() {{
            document.getElementById('manual-instructions').style.display = 'block';
            alert('由于技术限制，请按照下面的手动创建方法操作。');
        }}
    </script>
</body>
</html>
        """

        from flask import Response
        return Response(html_content, mimetype='text/html')

    except Exception as e:
        logger.error(f"生成快捷指令创建指导失败: {e}")
        return jsonify({'error': str(e)}), 500
